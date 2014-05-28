% Jiao Xianjun (putaoshu@gmail.com)
% convert gps signal bin log (http://www.jks.com/gps/gps.html) to hackrf format
% 
% after this script run:
% use gps_Nottingham.grc to playback gps.samples.8bit.IQ.fs5456.baseband.bin
% use rtl-sdr to capture signal: rtl_sdr -g 60 -f 1575.42e6 -s 2.8e6 -n 19.2e6 rtl_2.8Msps_1575.42MHz.bin
% use proc_rtl_bin_for_gps('rtl_2.8Msps_1575.42MHz.bin') to get 1bit bin
% see C/A result: gps_test rtl_2.8Msps_1575.42MHz_1bit.bin 0.62e6 2.8e6 100000
% C/a results are equal to http://www.jks.com/gps/gps.html
% 
% 2014-04-26

clear all; close all;
total_len = 446332928;
num_seg = 64;
sub_len = total_len/num_seg;

fid = fopen('gps.samples.1bit.I.fs5456.if4092.bin', 'r');
fid_new = fopen('gps.samples.8bit.IQ.fs5456.baseband.bin', 'w');

lo_real = int8( kron(ones(1, sub_len/4), [1 0 -1 0]) );
lo_imag = int8( kron(ones(1, sub_len/4), [0 1 0 -1]) );
for i=1:num_seg
    disp(num2str(i));
    
    y = int8( fread(fid, sub_len, 'ubit1').' );
    y = 1 - 2.*y;

    y = [y.*lo_real; y.*lo_imag];
    y = (y(:).').*100;

    fwrite(fid_new, y, 'int8');
end
fclose(fid);
fclose(fid_new);

% % paramters from gps spec
% base_sampling_rate = 1.023e6;
% code_len = 1023;
% fft_len = 4*code_len*4;
% 
% total_len = 446332928;
% % basic_len = 1743488; % 1743488*256 = 446332928
% num_seg = 16384;
% sub_len = total_len/num_seg;
% 
% % some parameters of raw data
% sampling_rate = 5.456e6;
% freq = 4.092e6;
% freq_shift_phase_per_sample = (sampling_rate-freq).*2.*pi./sampling_rate;
% % sampling_rate = 4.092e6;
% % freq = 5.456e6;
% % freq_shift_phase_per_sample = (freq - sampling_rate).*2.*pi./sampling_rate;
% 
% ov_sampling_rate = 4*base_sampling_rate;
% ts = 1/(sampling_rate); % 10.912Msps
% ts_new = 1/ov_sampling_rate; % 10.23Msps
% start_idx = 0;
% start_time = 0; % for 10.912Msps stream
% start_time_new = 0; % for 10.23Msps stream
% coef = fir1(30, 0.5); % baseband filter and upsampling filter
% len_tail = length(coef)-1;
% tail_data_baseband = zeros(1, len_tail)';
% tail_data_upsample = zeros(1, len_tail)';
% 
% % process block by block in case out of memory issue. write to hackrf bin file
% fid = fopen('gps.samples.1bit.I.fs5456.if4092.bin', 'r');
% if fid == -1
%     disp('Can not open file for reading!');
%     return;
% end
% % fid_new = fopen('gps.samples.8bit.I.fs5456.if4092_hackrf.bin', 'w');
% % if fid_new == -1
% %     disp('Can not open file for writing!');
% %     return;
% % end
% for i=1:1
%     disp([num2str(i) '/' num2str(num_seg)]);
%     
%     % read raw data
%     a = fread(fid, sub_len, 'ubit1', 0, 'b');
% 
%     % unsigned to signed
%     a = ( 1 - a.*2 );
%     
%     a = a - mean(a);
% 
%     % shift IF to baseband and filter out useless part
%     end_idx = start_idx + sub_len - 1;
%     idx_seq = (start_idx:end_idx)';
%     a = a.*exp(-1i.*idx_seq.*freq_shift_phase_per_sample );
%     start_idx = end_idx + 1;
%     
% %     a = conv(coef, a);
% %     a(1:len_tail) = a(1:len_tail) + tail_data_baseband;
% %     tail_data_baseband = a(end-len_tail+1:end);
% %     a = a(1:end-len_tail);
% 
% %     % 2x upsampling: 5.456Msps --> 10.912Msps
% %     a = upsample(a, 2);
% %     a = conv(coef, a);
% %     a(1:len_tail) = a(1:len_tail) + tail_data_upsample;
% %     tail_data_upsample = a(end-len_tail+1:end);
% %     a = a(1:end-len_tail);
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
%     % amplify to utilize 8bits DAC
%     a = 210.*a;
% %     
% %     % remove DC
% %     a = a - mean(a); % block based DC removal is not good, but let's try
%     
%     % fft inspect
%     a = a(end-fft_len+1:end);
%     s_fft = fft(a, fft_len);
%     ca_code = cacode(31);
%     
%     ca_code = kron(ca_code, [1 1 1 1]);
%     ca_code = ( 1 - ca_code.*2 );
%     ca_code = kron([1 1 1 1],ca_code);
%     ca_fft = conj(fft(ca_code, fft_len));
%     
% %     ca_code4 = [ca_code];
% %     ca_code4 = ( 1 - ca_code4.*2 );
% %     ca_code4 = upsample(ca_code4, 2);
% %     ca_code4 = conv(ca_code4, coef);
% %     ca_code4 = upsample(ca_code4, 2);
% %     ca_code4 = conv(ca_code4, coef);
% %     ca_fft = conj(fft(ca_code4, fft_len));
%     max_fo_idx = 5000;
%     corr_val = zeros(1, length(-max_fo_idx:max_fo_idx));
%     for fo_idx = -max_fo_idx:max_fo_idx
%         shift_tmp = circshift(ca_fft, [0, fo_idx]);
%         corr_val(fo_idx+max_fo_idx+1) = abs(sum(shift_tmp.*s_fft));
% %         if fo_idx == 0
% %             plot(abs(ifft(shift_tmp.*s_fft.')));
% %         end
%     end
%     plot(corr_val);
% 
% %     % interleave IQ and write to hackrf bin file
% %     a = [real(a);imag(a)];
% %     a = a(:).';
% % %     fwrite(fid_new, a, 'int8');
% end
% 
% fclose(fid);
% % fclose(fid_new);
