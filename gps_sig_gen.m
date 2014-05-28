% generate gps signal for gps_test
% Jiao Xianjun (putaoshu@gmail.com)
% 2014-05

clear all;
close all;

ca_base_rate = 1.023e6;
ca_ov_ratio = 8;
num_data = 100;
sv = 8;

num_ca_per_data = 20;
ca_rate = ca_base_rate*ca_ov_ratio;
g = ( 1 - 2.*cacode(sv, 1) );
g = upsample(g, ca_ov_ratio);
g = kron(ones(1, num_ca_per_data), g);

data = 1 - 2.*round(rand(1, num_data));
data = kron(data, g);

% % gen bin file for hackrf transmit
num = rcosine(1,ca_ov_ratio);
x = [data, data, data, data, data]; % ~10s
x = conv(num, x);
x = [x; zeros(1, length(x))].*50;
% x = [x; x].*50;
x = x(:).';
fid = fopen('gps_sig_tmp_for_hackrf_tx.bin', 'w'); % 8.184Msps
fwrite(fid, x, 'int8');
fclose(fid);

% % gen 1bit IF test signal to input to gps_test program
fc = ca_rate/4;
data = conv(data, num);
y = real(data.*exp(1i.*2.*pi.*fc.*(0:(length(data)-1)).*(1./ca_rate)));
y = (1-sign(y))./2;

fid = fopen('gps_sig_tmp.bin', 'w');
fwrite(fid, y, 'ubit1');
fclose(fid);
