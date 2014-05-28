% Jiao Xianjun (putaoshu@gmail.com)
% 2014-05

% rtl-sdr capture script:
% rtl_sdr -g 60 -f 1574.8e6  -s 2.8e6 -n 19.2e6 rtl_2.8Msps_1574.8MHz.bin
% rtl_sdr -g 60 -f 1575.42e6 -s 2.8e6 -n 19.2e6 rtl_2.8Msps_1575.42MHz.bin

function proc_rtl_bin_for_gps(rtl_bin_filename)

if strcmpi(rtl_bin_filename, 'rtl_2.8Msps_1574.8MHz.bin')
    fid = fopen('rtl_2.8Msps_1574.8MHz.bin', 'r');
    y = fread(fid, inf, 'uint8');
    fclose(fid);

    y = y - 128;
    y = y(1:2:end) + 1i.*y(2:2:end);
    y = y - mean(y);
%     plot(real(y(1:1e4)));

    y = real(y); % imag(y) also works
    
    y = (1-sign(y))./2;

    fid = fopen('rtl_2.8Msps_1574.8MHz_1bit.bin', 'w');
    fwrite(fid, y, 'ubit1');
    fclose(fid);
    
    msgbox('RUN: gps_test rtl_2.8Msps_1574.8MHz_1bit.bin 0.62e6 2.8e6 100000');
elseif strcmpi(rtl_bin_filename, 'rtl_2.8Msps_1575.42MHz.bin')

    fid = fopen('rtl_2.8Msps_1575.42MHz.bin', 'r');
    y = fread(fid, inf, 'uint8');
    fclose(fid);

    y = y - 128;
    y = y(1:2:end) + 1i.*y(2:2:end);
    y = y - mean(y);
%     plot(real(y(1:1e4)));

    fc = 0.62e6;
    y = real( y.'.*exp(1i.*2.*pi.*fc.*(0:(length(y)-1)).*(1./2.8e6)) );

    y = (1-sign(y))./2;

    fid = fopen('rtl_2.8Msps_1575.42MHz_1bit.bin', 'w');
    fwrite(fid, y, 'ubit1');
    fclose(fid);
    
    msgbox('RUN: gps_test rtl_2.8Msps_1575.42MHz_1bit.bin 0.62e6 2.8e6 100000');
else
    disp('filename must be rtl_2.8Msps_1574.8MHz.bin or rtl_2.8Msps_1575.42MHz.bin!');
    return;
end

% % % ----------------------backup----------------------
% fid = fopen('rtl_3.2Msps_1575.42MHz.bin', 'r');
% y = fread(fid, inf, 'uint8');
% fclose(fid);
% 
% y = y - 128;
% y = y(1:2:end) + 1i.*y(2:2:end);
% y = y - mean(y);
% % plot(abs(fft(y(1:3e6))));
% plot(real(y(1:1e4)));
% 
% fc = 0.8e6;
% y = real( y.'.*exp(1i.*2.*pi.*fc.*(0:(length(y)-1)).*(1./3.2e6)) );
% 
% y = (1-sign(y))./2;
% 
% fid = fopen('rtl_3.2Msps_1575.42MHz_1bit.bin', 'w');
% fwrite(fid, y, 'ubit1');
% fclose(fid);

% fid = fopen('rtl_3.069Msps_1575.42MHz.bin', 'r');
% y = fread(fid, inf, 'uint8');
% fclose(fid);
% 
% y = y - 128;
% y = y(1:2:end) + 1i.*y(2:2:end);
% y = y - mean(y);
% plot(real(y(1:1e4)));
% 
% fc = 3.069e6/4;
% y = real( y.'.*exp(1i.*2.*pi.*fc.*(0:(length(y)-1)).*(1./3.069e6)) );
% 
% y = (1-sign(y))./2;
% 
% fid = fopen('rtl_3.069Msps_1575.42MHz_1bit.bin', 'w');
% fwrite(fid, y, 'ubit1');
% fclose(fid);