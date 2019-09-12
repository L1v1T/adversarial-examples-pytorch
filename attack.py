from model import Net
from PIL import Image
import torch
from torchvision import transforms
from my_dataset import MyDataset
import argparse
import math
import time
import random

import numpy as np

def classifies(model, image):
    outputs = model(image)
    print(outputs)
    log_prob, predicted = torch.max(outputs, 1)
    print(math.exp(log_prob[0].data))
    return predicted

def FGMS(model, ori_image, epsilon=0.33):
    image = ori_image.clone().detach()
    outputs = model(image)
    _, predicted = torch.max(outputs, 1)

    image_var = image.clone().detach().requires_grad_(True)
    attackoutputs = model(image_var)
    model.zero_grad()
    loss = torch.nn.functional.nll_loss(attackoutputs, predicted)
    loss.backward()
    
    grad_sign = image_var.grad.sign()
    image += epsilon * grad_sign

    image = torch.clamp(image, 0, 1)
    
    return image, 1

def I_FGMS(model, ori_image, epsilon=0.07):
    image = ori_image.clone().detach()
    outputs = model(image)
    _, predicted = torch.max(outputs, 1)
    attacklabel = predicted.clone().detach()
    count = 0
    while torch.equal(attacklabel.float(), predicted.float()):
        image_var = image.clone().detach().requires_grad_(True)
        attackoutputs = model(image_var)
        model.zero_grad()
        loss = torch.nn.functional.nll_loss(attackoutputs, predicted)
        loss.backward()
        
        grad_sign = image_var.grad.sign()
        image += epsilon * grad_sign
        '''
        image += epsilon * image_var.grad
        '''

        image = torch.clamp(image, 0, 1)
        attackoutputs = model(image)
        _, attacklabel = torch.max(attackoutputs, 1)
        count += 1
    
    return image, count

def fixed_I_FGMS(model, ori_image, epsilon=7):
    image = ori_image.clone().detach()
    outputs = model(image)
    _, predicted = torch.max(outputs, 1)
    attacklabel = predicted.clone().detach()
    count = 0
    while torch.equal(attacklabel.float(), predicted.float()):
        image_var = image.clone().detach().requires_grad_(True)
        attackoutputs = model(image_var)
        model.zero_grad()
        loss = torch.nn.functional.nll_loss(attackoutputs, predicted)
        loss.backward()
        '''
        grad_sign = image_var.grad.sign()
        image += epsilon * grad_sign
        '''
        image += epsilon * image_var.grad
        
        image = torch.clamp(image, 0, 1)
        attackoutputs = model(image)
        _, attacklabel = torch.max(attackoutputs, 1)
        count += 1
    
    return image, count

Z_x = 0

def f6(model, x, target, k=0.0):
    # choose a random target
    # print("****************************")
    model(x)
    indices = torch.tensor([target])
    # print(Z_x)
    # print(torch.nn.functional.softmax(Z_x, dim=1))
    Z_x_t = torch.index_select(Z_x, 1, indices)
    # print(Z_x_t)

    ilist = []
    for i in range(Z_x.size()[1]):
        ilist.append(i)
    ilist.remove(target)
    indices = torch.tensor(ilist)

    Z_is = torch.index_select(Z_x, 1, indices)
    # print(Z_is)

    Z_is_max, i = torch.max(Z_is, 1)
    Z_is_max = Z_is_max.unsqueeze(0)
    # print(Z_is_max)
    Z_i_t = Z_is_max - Z_x_t

    # print("i")
    # print(i)
    # print("Z_i")
    # print(Z_is_max)
    # print("Z_t")
    # print(Z_x_t)
    # print("sub")
    # print(Z_i_t)
    # print("****************************")
    
    confidence = torch.tensor([[-k]])
    # print(confidence)
    if confidence > Z_i_t:
        return confidence
    else:
        return Z_i_t

def f2(model, x, target, k=0.0):
    # choose a random target
    # print("****************************")
    F_x = model(x)
    indices = torch.tensor([target])
    # print(F_x)
    # print(torch.nn.functional.softmax(F_x, dim=1))
    F_x_t = torch.index_select(F_x, 1, indices)
    # print(Z_x_t)

    ilist = []
    for i in range(F_x.size()[1]):
        ilist.append(i)
    ilist.remove(target)
    indices = torch.tensor(ilist)

    F_is = torch.index_select(F_x, 1, indices)
    # print(Z_is)

    F_is_max, i = torch.max(F_is, 1)
    F_is_max = F_is_max.unsqueeze(0)
    # print(Z_is_max)
    F_i_t = F_is_max - F_x_t

    # print("i")
    # print(i)
    # print("F_i")
    # print(F_is_max)
    # print("F_t")
    # print(F_x_t)
    # print("sub")
    # print(F_i_t)
    # print("****************************")
    
    confidence = torch.tensor([[-k]])
    # print(confidence)
    if confidence > F_i_t:
        return confidence
    else:
        return F_i_t

def CW_L2(model, ori_image, c, label, fn, iter):
    # def func_Z(self, input, output):
    #     global Z_x
    #     Z_x = output.data
    # model.fc2.register_forward_hook(func_Z)

    target = random.randint(0, model.fc2.out_features - 1)
    while target == label:
        target = random.randint(0, model.fc2.out_features - 1)
    print("target")
    print(target)
    # print(Z_x.size()[1])

    # define new variable omega and perturbation delta
    omega = torch.zeros(ori_image.size(), requires_grad=True)
    # delta = 0.5 * (torch.tanh(omega) + 1)
    
    # print(f6(model, delta, label))

    
    # print(omega)
    # print(omega.grad)
    # print(type(modify))
    # omega = omega - modify
    # print(omega)
    for _ in range(iter - 1):
        # objective.zero_grad()
        omega_var = omega.clone().detach().requires_grad_(True)
        ad_data = 0.5 * (torch.tanh(omega_var) + 1)
        # objective = torch.norm((delta - ori_image)) + c * f6(model, delta, target)
        # k 的影响很大
        objective = torch.norm((ad_data - ori_image)) + c * f2(model, ad_data, target, 0.0)
        objective.backward(retain_graph=True)
        omega = omega - (0.5 * omega_var.grad)

    return ad_data

def evaluate(model, data_set, num_data, eps, attackfunc):
    count = 0
    mean_sum = 0
    time_sum = 0
    succeed_num = 0.0
    ite_sum = 0.0
    for data, _ in data_set:
        data = data.unsqueeze(0)
        tstart = time.time()
        adv_img, ite_num = attackfunc(model, data, eps)
        ite_sum += ite_num
        tend = time.time()
        time_sum += (tend - tstart)
        pertur = torch.abs(data - adv_img)
        mean_sum += torch.mean(pertur)
        
        attackoutputs = model(data)
        _, attack_label = torch.max(attackoutputs, 1)
        originaloutputs = model(adv_img)
        _, original_label = torch.max(originaloutputs, 1)
        if not torch.equal(attack_label.float(), original_label.float()):
            succeed_num += 1.0
        count += 1
        if count == num_data:
            break
    return (mean_sum / count), (time_sum / count), (succeed_num / count), succeed_num, count, (ite_sum / count)

def main():
    
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                        help='input batch size for training (default: 64)')
    parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                        help='input batch size for testing (default: 1000)')
    parser.add_argument('--epochs', type=int, default=10, metavar='N',
                        help='number of epochs to train (default: 10)')
    parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                        help='learning rate (default: 0.01)')
    parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                        help='SGD momentum (default: 0.5)')
    parser.add_argument('--no-cuda', action='store_true', default=False,
                        help='disables CUDA training')
    parser.add_argument('--seed', type=int, default=1, metavar='S',
                        help='random seed (default: 1)')
    parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                        help='how many batches to wait before logging training status')
    
    parser.add_argument('--save-model', action='store_true', default=False,
                        help='For Saving the current Model')
    args = parser.parse_args()
    use_cuda = not args.no_cuda and torch.cuda.is_available()

    torch.manual_seed(args.seed)

    device = torch.device("cuda" if use_cuda else "cpu")

    kwargs = {'num_workers': 1, 'pin_memory': True} if use_cuda else {}

    model = Net().to(device)
    model.load_state_dict(torch.load("mnist_cnn.pt"))
    model.eval()
    image = Image.open("attack.png").convert("L")
    #image = Image.open("look.png").convert("L")
    #image.show()
    '''
    trans = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((0.1307,), (0.3081,))
                ])
    '''
    trans = transforms.Compose([transforms.ToTensor()])
    
    image = trans(image)
    # print(len(image))
    # print(len(image[0]))
    # print(len(image[0][0]))
    #print(len(image[0][0][0]))
    image = image.unsqueeze(0)
    prediction = classifies(model, image)
    print(prediction)
    # print(len(image))
    # print(len(image[0]))
    # print(len(image[0][0]))
    # print(len(image[0][0][0]))
    
    #print("original image")
    #print(image)

    # new_sample, _ = fixed_I_FGMS(model, image, epsilon = 0.07)
    new_sample = CW_L2(model, image, 5.0, prediction, f2, 600)
    new_sample = new_sample.detach()
    #print("new image")
    #print(new_sample)
    print(classifies(model, new_sample))
    new_sample = new_sample.squeeze(0)
    image = image.squeeze(0)
    #print(image.size())
    perturbation = torch.abs(new_sample - image)
    print(torch.norm(perturbation))
    b=np.array(new_sample)  #b.shape  (1,64,64)
    maxi=b.max()
    b=b*255./maxi
    b=b.transpose(1,2,0).astype(np.uint8)
    b=np.squeeze(b,axis=2)
    xx=Image.fromarray(b)
    xx.save("look.png")
    
    b=np.array(perturbation)  #b.shape  (1,64,64)
    maxi=b.max()
    b=b*255./maxi
    b=b.transpose(1,2,0).astype(np.uint8)
    b=np.squeeze(b,axis=2)
    xx=Image.fromarray(b)
    xx.save("pertubation.png")
    #new_image = Image.fromarray(new_sample)
    #new_image.show()

    data_loader = torch.utils.data.DataLoader(
        MyDataset("test", transform=transforms.Compose([transforms.ToTensor()])),
        batch_size=args.test_batch_size, shuffle=True, **kwargs)

    # # image data
    # print(data_loader.dataset[0])
    # print(len(data_loader.dataset[0][0]))
    # print(len(data_loader.dataset[0][0][0]))
    # print(len(data_loader.dataset[0][0][0][0]))
    # print(data_loader.dataset[0][0][0][0])
    # exit(0)
    # print((data_loader))
    # for data, t in data_loader:
    #     print(len(data))
    #     print(len(data[0]))
    #     print(len(data[0][0]))
    #     print(len(data[0][0][0]))
    #     print(len(t))
    #     break
    # exit(0)
    # print("Evaluating FGSM")
    # print(evaluate(model, data_loader.dataset, 5000, 0.33, FGMS))
    # print("Evaluating I-FGSM")
    # print(evaluate(model, data_loader.dataset, 5000, 0.07, I_FGMS))
    # print("Evaluating my I-FGSM")
    # print(evaluate(model, data_loader.dataset, 5000, 10, fixed_I_FGMS))

if __name__ == "__main__":
    main()