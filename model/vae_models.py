import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import torch.optim as optim

class MNIST_Dataset(Dataset):    
    def __init__(self, image):
        super(MNIST_Dataset).__init__()
        self.image = image
    def __len__(self):
        return self.image.shape[0]
    def __getitem__(self, idx):
        return np.random.binomial(1, self.image[idx, :]).astype('float32')

class OMNIGLOT_Dataset(Dataset):
    def __init__(self, image):
        super(OMNIGLOT_Dataset).__init__()
        self.image = image
    def __len__(self):
        return self.image.shape[0]
    def __getitem__(self, idx):
        return self.image[idx, :]
    
class IWAE_Decoder(nn.Module):
    def __init__(self, hidden_size, output_size):
        super(IWAE_Decoder, self).__init__()
        
        self.hidden_size = hidden_size
        self.output_size = output_size

        self.transform = nn.Sequential(
            nn.Linear(hidden_size, 200),
            nn.Tanh(),
            nn.Linear(200, 200),
            nn.Tanh(),
            nn.Linear(200, output_size),
            nn.Sigmoid())
    
    def forward(self, h):
        p = self.transform(h)
        return p

    def calc_logPxh(self, x, h):
        log_Ph = torch.sum(-0.5*h**2 - 0.5*torch.log(2*h.new_tensor(np.pi)), -1)
        p = self.forward(h)
        log_PxGh = torch.sum(x*torch.log(p) + (1-x)*torch.log(1-p), -1)        
        logPxh = log_Ph + log_PxGh
        return logPxh    
    

class IWAE_Encoder(nn.Module):
    def __init__(self, input_size, hidden_size):
        super(IWAE_Encoder, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size

        self.transform = nn.Sequential(
            nn.Linear(input_size, 200),
            nn.Tanh(),
            nn.Linear(200, 200),
            nn.Tanh())
        self.fc_mu = nn.Linear(200, hidden_size)
        self.fc_logsigma = nn.Linear(200, hidden_size)

    def forward(self, x):
        out = self.transform(x)
        mu = self.fc_mu(out)
        logsigma = self.fc_logsigma(out)
        sigma = torch.exp(logsigma)
        return mu, sigma
            
    def calc_logQhGx(self, x, h):
        mu, sigma = self.forward(x)
        log_QhGx = torch.sum(-0.5*((h-mu)/sigma)**2-0.5*torch.log(2*mu.new_tensor(np.pi)*sigma**2), -1)
        return log_QhGx

    
# class IWAE_1(nn.Module):
#     def __init__(self, dim_h1, dim_image_vars):
#         super(IWAE_1, self).__init__()
#         self.dim_h1 = dim_h1
#         self.dim_image_vars = dim_image_vars

#         ## encoder
#         self.encoder_h1 = BasicBlock(dim_image_vars, 200, dim_h1)
        
#         ## decoder
#         self.decoder_x =  nn.Sequential(nn.Linear(dim_h1, 200),
#                                         nn.Tanh(),
#                                         nn.Linear(200, 200),
#                                         nn.Tanh(),
#                                         nn.Linear(200, dim_image_vars),
#                                         nn.Sigmoid())
        
#     def encoder(self, x):
#         mu_h1, sigma_h1 = self.encoder_h1(x)
#         eps = Variable(sigma_h1.data.new(sigma_h1.size()).normal_())
#         h1 = mu_h1 + sigma_h1 * eps                
#         return h1, mu_h1, sigma_h1, eps
    
#     def decoder(self, h1):
#         p = self.decoder_x(h1)
#         return p
    
#     def forward(self, x):
#         h1, mu_h1, sigma_h1, eps = self.encoder(x)
#         p = self.decoder(h1)
#         return (h1, mu_h1, sigma_h1, eps), (p)

#     def train_loss(self, inputs):
#         h1, mu_h1, sigma_h1, eps = self.encoder(inputs)
#         #log_Qh1Gx = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         log_Qh1Gx = torch.sum(-0.5*(eps)**2 - torch.log(sigma_h1), -1)
        
#         p = self.decoder(h1)
#         log_Ph1 = torch.sum(-0.5*h1**2, -1)
#         log_PxGh1 = torch.sum(inputs*torch.log(p) + (1-inputs)*torch.log(1-p), -1)

#         log_weight = log_Ph1 + log_PxGh1 - log_Qh1Gx
#         log_weight = log_weight - torch.max(log_weight, 0)[0]
#         weight = torch.exp(log_weight)
#         weight = weight / torch.sum(weight, 0)
#         weight = Variable(weight.data, requires_grad = False)
#         loss = -torch.mean(torch.sum(weight * (log_Ph1 + log_PxGh1 - log_Qh1Gx), 0))
#         return loss

#     def test_loss(self, inputs):
#         h1, mu_h1, sigma_h1, eps = self.encoder(inputs)
#         #log_Qh1Gx = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         log_Qh1Gx = torch.sum(-0.5*(eps)**2 - torch.log(sigma_h1), -1)
        
#         p = self.decoder(h1)
#         log_Ph1 = torch.sum(-0.5*h1**2, -1)
#         log_PxGh1 = torch.sum(inputs*torch.log(p) + (1-inputs)*torch.log(1-p), -1)

#         log_weight = log_Ph1 + log_PxGh1 - log_Qh1Gx
#         weight = torch.exp(log_weight)
#         loss = -torch.mean(torch.log(torch.mean(weight, 0)))        
#         return loss

    
# class IWAE_2(nn.Module):
#     def __init__(self, dim_h1, dim_h2, dim_image_vars):
#         super(IWAE_2, self).__init__()

#         self.dim_h1 = dim_h1
#         self.dim_h2 = dim_h2
#         self.dim_image_vars = dim_image_vars

#         ## encoder
#         self.encoder_h1 = BasicBlock(dim_image_vars, 200, dim_h1)
#         self.encoder_h2 = BasicBlock(dim_h1, 100, dim_h2)
        
#         ## decoder
#         self.decoder_h1 = BasicBlock(dim_h2, 100, dim_h1)        
#         self.decoder_x =  nn.Sequential(nn.Linear(dim_h1, 200),
#                                         nn.Tanh(),
#                                         nn.Linear(200, 200),
#                                         nn.Tanh(),
#                                         nn.Linear(200, dim_image_vars),
#                                         nn.Sigmoid())
        
#     def encoder(self, x):
#         mu_h1, sigma_h1 = self.encoder_h1(x)
#         eps1 = Variable(sigma_h1.data.new(sigma_h1.size()).normal_())
#         h1 = mu_h1 + sigma_h1 * eps1
        
#         mu_h2, sigma_h2 = self.encoder_h2(h1)
#         eps2 = Variable(sigma_h2.data.new(sigma_h2.size()).normal_())
#         h2 = mu_h2 + sigma_h2 * eps2
        
#         return (h1, mu_h1, sigma_h1, eps1), (h2, mu_h2, sigma_h2, eps2)
    
#     def decoder(self, h1, h2):
#         mu_h1, sigma_h1 = self.decoder_h1(h2)
#         p = self.decoder_x(h1)
#         return (h1, mu_h1, sigma_h1), (p)
    
#     def forward(self, x):
#         (h1, mu_h1, sigma_h1), (h2, mu_h2, sigma_h2) = self.encoder(x)
#         p = self.decoder(h2)        
#         return ((h1, mu_h1, sigma_h1, eps1), (h2, mu_h2, sigma_h2, eps2)), (p)

#     def train_loss(self, inputs):
#         (h1, mu_h1, sigma_h1, eps1), (h2, mu_h2, sigma_h2, eps2) = self.encoder(inputs)
#         # log_Qh1Gx = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         # log_Qh2Gh1 = torch.sum(-0.5*((h2-mu_h2)/sigma_h2)**2 - torch.log(sigma_h2), -1)

#         log_Qh1Gx = torch.sum(-0.5*(eps1)**2 - torch.log(sigma_h1), -1)
#         log_Qh2Gh1 = torch.sum(-0.5*(eps2)**2 - torch.log(sigma_h2), -1)
        
        
#         (h1, mu_h1, sigma_h1), (p) = self.decoder(h1, h2)
#         log_Ph2 = torch.sum(-0.5*h2**2, -1)
#         log_Ph1Gh2 = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         log_PxGh1 = torch.sum(inputs*torch.log(p) + (1-inputs)*torch.log(1-p), -1)

#         log_weight = log_Ph2 + log_Ph1Gh2 + log_PxGh1 - log_Qh1Gx - log_Qh2Gh1
#         log_weight = log_weight - torch.max(log_weight, 0)[0]
#         weight = torch.exp(log_weight)
#         weight = weight / torch.sum(weight, 0)
#         weight = Variable(weight.data, requires_grad = False)
#         loss = -torch.mean(torch.sum(weight * (log_Ph2 + log_Ph1Gh2 + log_PxGh1 - log_Qh1Gx - log_Qh2Gh1), 0))
#         return loss

#     def test_loss(self, inputs):
#         (h1, mu_h1, sigma_h1, eps1), (h2, mu_h2, sigma_h2, eps2) = self.encoder(inputs)
#         # log_Qh1Gx = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         # log_Qh2Gh1 = torch.sum(-0.5*((h2-mu_h2)/sigma_h2)**2 - torch.log(sigma_h2), -1)
#         log_Qh1Gx = torch.sum(-0.5*(eps1)**2 - torch.log(sigma_h1), -1)
#         log_Qh2Gh1 = torch.sum(-0.5*(eps2)**2 - torch.log(sigma_h2), -1)
        
#         (h1, mu_h1, sigma_h1), (p) = self.decoder(h1, h2)
#         log_Ph2 = torch.sum(-0.5*h2**2, -1)
#         log_Ph1Gh2 = torch.sum(-0.5*((h1-mu_h1)/sigma_h1)**2 - torch.log(sigma_h1), -1)
#         log_PxGh1 = torch.sum(inputs*torch.log(p) + (1-inputs)*torch.log(1-p), -1)
        
#         log_weight = log_Ph2 + log_Ph1Gh2 + log_PxGh1 - log_Qh1Gx - log_Qh2Gh1
#         weight = torch.exp(log_weight)
#         loss = -torch.mean(torch.log(torch.mean(weight, 0)))
        
#         return loss
    
