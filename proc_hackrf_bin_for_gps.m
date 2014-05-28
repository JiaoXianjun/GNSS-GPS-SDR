% Jiao Xianjun (putaoshu@gmail.com)
% 2014-05

clear all;
close all;

fid = fopen('hackrf_ant3_10Msps_2.5Mbw_1575.42MHz.bin', 'r');
y = fread(fid, inf, 'int8');
fclose(fid);

y = y(1:2:end) + 1i.*y(2:2:end);

y = y - mean(y);

y = real( y.'.*exp(1i.*(0:(length(y)-1) ).*2.6e6.*2.*pi./10e6 ) );
y = (1-sign(y))./2;

fid = fopen('hackrf_ant3_tmp.bin', 'w');
fwrite(fid, y, 'ubit1');
fclose(fid);
