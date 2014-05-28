% Jiao Xianjun (putaoshu@gmail.com)
% convert gps signal bin log (http://www.jks.com/gps/gps.html) to hackrf format
% 
% usage of hackrf_transfer
% hackrf_transfer -s 10000000 -f 1575420000 -b 2500000 -t gps.samples.8bit.I.fs5456.if4092_hackrf.bin
% 
% 2014-04-26

clear all; close all;

% process block by block in case out of memory issue. write to hackrf bin file
fid = fopen('gps.samples.8bit.IQinterleave.fs5456.if0.bin', 'r');
if fid == -1
    disp('Can not open file for reading!');
    return;
end
fid_new = fopen('gps.samples.8bit.IQinterleave.fs5456.if0.noDC.bin', 'w');
if fid_new == -1
    disp('Can not open file for writing!');
    return;
end

a = fread(fid, inf, 'int8');
a(1:2:end) = a(1:2:end) - mean(a(1:2:end));
a(2:2:end) = a(2:2:end) - mean(a(2:2:end));
fwrite(fid_new, a, 'int8');

fclose(fid);
fclose(fid_new);

% total_len = 446332928;
% % basic_len = 1743488; % 1743488*256 = 446332928
% num_seg = 32;
% sub_len = total_len/num_seg;
% 
% % some parameters of raw data
% sampling_rate = 5.456e6;
% 
% ov_sampling_rate = 10e6;
% ts = 1/(2*sampling_rate); % 10.912Msps
% ts_new = 1/ov_sampling_rate; % 10.23Msps
% start_idx = 0;
% start_time = 0; % for 10.912Msps stream
% start_time_new = 0; % for 10.23Msps stream
% coef = fir1(62, 0.5); % baseband filter and upsampling filter
% len_tail = length(coef)-1;
% tail_data_baseband = zeros(1, len_tail)';
% tail_data_upsample = zeros(1, len_tail)';
% 
% % process block by block in case out of memory issue. write to hackrf bin file
% fid = fopen('gps.samples.8bit.IQinterleave.fs5456.if0.bin', 'r');
% if fid == -1
%     disp('Can not open file for reading!');
%     return;
% end
% fid_new = fopen('gps.samples.8bit.IQinterleave.fs10000.if0.bin', 'w');
% if fid_new == -1
%     disp('Can not open file for writing!');
%     return;
% end
% 
% for i=1:num_seg
%     disp([num2str(i) '/' num2str(num_seg)]);
%     
%     % read raw data
%     a = fread(fid, sub_len, 'int8');
%     
%     disp(num2str(length(a)));
%     
%     a = a(1:2:end) + 1i.*a(2:2:end);
% 
%     a = a - mean(a);
% 
%     a = conv(coef, a);
%     a(1:len_tail) = a(1:len_tail) + tail_data_baseband;
%     tail_data_baseband = a(end-len_tail+1:end);
%     a = a(1:end-len_tail);
% 
%     % 2x upsampling: 5.456Msps --> 10.912Msps
%     a = upsample(a, 2);
%     a = conv(coef, a);
%     a(1:len_tail) = a(1:len_tail) + tail_data_upsample;
%     tail_data_upsample = a(end-len_tail+1:end);
%     a = a(1:end-len_tail);
% 
%     % resampling 10.912Msps to 10.23Msps which is hackrf friendly
%     time_seq = start_time + (0:(length(a)-1)).*ts;
%     end_time = time_seq(end);
%     num_time_point_new = floor( (end_time - start_time)/ts_new ) + 1;
%     time_seq_new = start_time_new + (0:(num_time_point_new-1)).*ts_new;
%     end_time_new = time_seq_new(end);
%     disp(num2str([start_time, end_time, length(time_seq), start_time_new, end_time_new, length(time_seq_new)]));
%     a = interp1( time_seq, a, time_seq_new, 'linear', 'extrap');
% %     plot(time_seq, 'b.'); hold on; plot(time_seq_new, 'r.');
%     start_time = end_time + ts;
%     start_time_new = end_time_new + ts_new;
% 
%     % interleave IQ and write to hackrf bin file
%     a = [real(a);imag(a)];
%     a = a(:).';
%     fwrite(fid_new, a, 'int8');
%     disp(num2str(length(a)));
% end
% 
% fclose(fid);
% fclose(fid_new);
