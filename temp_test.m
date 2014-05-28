% function temp_test

clear all;
close all;

coef = [-1 2 3 -4 2];
s = randn(1, 400);
b = conv(s, coef);

tail_data = zeros(1, 4);
c = zeros(1, length(s));
for i=1:4
    sp = (i-1)*100 + 1;
    ep = sp + 99;
    a = s(sp:ep);
    
    a = conv(a, coef);
    a(1:4) = a(1:4) + tail_data;
    tail_data = a(end-3:end);
    a = a(1:end-4);
    
    c(sp:ep) = a;
end

subplot(2,1,1); plot(b); hold on; plot(c,'r.');
subplot(2,1,2); plot(c - b(1:400));
