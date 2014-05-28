% Jiao Xianjun (putaoshu@gmail.com)
% 2014-04-25

% function gps_wav_log2bin(filename)

% filename_out = [filename(1:(end-4)) '.bin'];
% 
% % y = audioread(filename, [1 10000]);
% % y = y(:,1) + 1i.*y(:,2); %plot(abs(fft(y(1:3e6))));
% % max_val = max([abs(real(y)); abs(imag(y)) ]);
% % scale_factor = 127/max_val;
% % y = y.*scale_factor;
% 
% y = audioread(filename);
% y = y';
% y = y(:)';
% max_val = max(y);
% scale_factor = 127/max_val;
% y = y.*scale_factor;
% y = y - mean(y);
% 
% fid = fopen(filename_out, 'w');
% fwrite(fid, y, 'int8');
% fclose(fid);

clear all;
close all;
[y, fs] = audioread('HDSDR_20140421_080645Z_1574800kHz_RF.wav', 'native');
% % y = (1-sign(y))./2;
% y = y(:,1) + 1i.*y(:,2);
% y = real( y.'.*exp(1i.*(0:(length(y)-1) ).*0.38e6.*2.*pi./2.8e6 ) );
% y = y - mean(y);
% y = (1-sign(y))./2;
% 
% fid = fopen('HDSDR_20140421_080645Z_1574800kHz_RF_I.bin', 'w');
% fwrite(fid, y, 'ubit1');
% fclose(fid);

% y(:,1) = y(:,1) - mean(y(:,1));
% y(:,2) = y(:,2) - mean(y(:,2));
% plot((y(1:1e4,1))); hold on; plot((y(1:1e4,2)), 'r');
% 
% y = (1-sign(y))./2;
% fid = fopen('HDSDR_20140421_080645Z_1574800kHz_RF_I.bin', 'w');
% fwrite(fid, y(:,1), 'ubit1');
% fclose(fid);

% fid = fopen('HDSDR_20140421_080645Z_1574800kHz_RF_Q.bin', 'w');
% fwrite(fid, y(:,2), 'ubit1');
% fclose(fid);

y = y.';
y = y(:).';
y = y - mean(y);
y = (1-sign(y))./2;
fid = fopen('HDSDR_20140421_080645Z_1574800kHz_RF_1bit.bin', 'w');
fwrite(fid, y, 'ubit1');
fclose(fid);

