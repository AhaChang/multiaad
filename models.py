import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.parameter import Parameter
from torch.nn.modules.module import Module

class GraphConvolution(Module):
    """
    Simple GCN layer, similar to https://arxiv.org/abs/1609.02907
    """

    def __init__(self, in_features, out_features, bias=True):
        super(GraphConvolution, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = Parameter(torch.FloatTensor(in_features, out_features))
        if bias:
            self.bias = Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weight.size(1))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.uniform_(-stdv, stdv)

    def forward(self, input, adj):
        support = torch.mm(input, self.weight)
        output = torch.spmm(adj, support)
        if self.bias is not None:
            return output + self.bias
        else:
            return output

    def __repr__(self):
        return self.__class__.__name__ + ' (' \
               + str(self.in_features) + ' -> ' \
               + str(self.out_features) + ')'
    

class Encoder(nn.Module):
    def __init__(self, nfeat, nhid, dropout):
        super(Encoder, self).__init__()

        self.gc1 = GraphConvolution(nfeat, nhid, bias=True)
        self.gc2 = GraphConvolution(nhid, nhid, bias=True)
        self.dropout = dropout

    def forward(self, x, adj):
        x = F.dropout(x, self.dropout, training=self.training)
        x = F.relu(self.gc1(x, adj))
        x = F.dropout(x, self.dropout, training=self.training)
        x = self.gc2(x, adj)
        return x


class Discriminator(nn.Module):
    def __init__(self, nin, nout, dropout):
        super(Discriminator, self).__init__()

        self.lr1 = nn.Linear(nin, nin//2)
        self.lr2 = nn.Linear(nin//2, nout)
        self.dropout = dropout

    def forward(self, x):
        x = F.relu(x)
        x = F.dropout(x, self.dropout, training=self.training)
        x = F.relu(self.lr1(x))
        x = F.dropout(x, self.dropout, training=self.training)
        x = self.lr2(x)
        return x
    
    
class MultiTask(nn.Module):
    def __init__(self, nfeat, nhid, nout, dropout):
        super(MultiTask, self).__init__()

        self.encoder = Encoder(nfeat, nhid, dropout)
        self.dis_neighbor = Discriminator(nhid, nout, dropout)
        self.dis_anomlay = Discriminator(nhid, 2, dropout) 

    def forward(self, x, adj):
        x = self.encoder(x, adj)

        pred_nc = self.dis_neighbor(x)
        pred_ad = self.dis_anomlay(x)

        return x, pred_nc, pred_ad
    

class SingleTask(nn.Module):
    def __init__(self, nfeat, nhid, nout, dropout):
        super(SingleTask, self).__init__()

        self.encoder = Encoder(nfeat, nhid, dropout)
        self.discriminator = Discriminator(nhid, nout, dropout)

    def forward(self, x, adj):
        x = self.encoder(x, adj)
        pred = self.discriminator(x)

        return x, pred