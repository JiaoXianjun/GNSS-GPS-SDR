function g=cacode(sv,fs)
% function G=CACODE(SV,FS) 
% Generates 1023 length C/A Codes for GPS PRNs 1-37
%
% 
% g: nx1023 matrix- with each PRN in each row with symbols 1 and 0
% sv: a row or column vector of the SV's to be generated
% 	 valid entries are 1 to 37
% fs: optional number of samples per chip (defaults to 1), fractional samples allowed, must be 1 or greater.
%
% For multiple samples per chip, function is a zero order hold. 
%
%
% For example to generate the C/A codes for PRN 6 and PRN 12 use:
% g=cacode([6 12]),
% and to generate the C/A codes for PRN 6 and PRN 12 at 5 MHz use
% g=cacode([6 12],5/1.023)
% 
%
% For more information refer to the "GPS SPS Signal Specification"
% http://www.navcen.uscg.gov/pubs/gps/sigspec/default.htm
%
% Dan Boschen 12-30-2007
% boschen@loglin.com

% Revision History
% rev 1.0 Dan Boschen 4-15-2007  Initial Release
%
% rev 1.1 Dan Boschen 7-15-2007  Corrected error with taps for PRN30, should be [2,7] was 
% 					incorrect as [1 7]. Thank you Jadah Zak for finding this.
%
%
% rev 1.2 Dan Boschen 12-26-2007 Fixed column index error when ceil ~ L 
%				Thank you Jared Meadows for finding this.
%
% rev 1.3 Dan Boschen 12-30-2007 Changed comment "first order hold" to
% "zero order hold".
%
% rev 1.4 Dan Boschen 6-1-2010   Updated email address in comments



if nargin<2
	fs=1;
end


if (max(sv)>37) || (min(sv)<1) || (min(size(sv))~=1)
	error('sv must be a row or column vector with integers between 1 and 37\n')
end

if fs<1
	error('fs must be 1 or greater\n')
end	

% force integers
testint=round(sv)-sv;
if testint ~= 0 
	warning('non-integer value entered for sv, rounding to closest integer\n');
	sv = round(sv);
end


% table of C/A Code Tap Selection (sets delay for G2 generator)
tap=[2 6;
    3 7;
    4 8;
    5 9;
    1 9;
    2 10;
    1 8;
    2 9;
    3 10;
    2 3;
    3 4;
    5 6;
    6 7;
    7 8;
    8 9;
    9 10;
    1 4;
    2 5;
    3 6;
    4 7;
    5 8;
    6 9;
    1 3;
    4 6;
    5 7;
    6 8;
    7 9;
    8 10;
    1 6;
    2 7;
    3 8;
    4 9
    5 10
    4 10
    1 7
    2 8
    4 10];

% G1 LFSR: x^10+x^3+1
s=[0 0 1 0 0 0 0 0 0 1];
n=length(s);
g1=ones(1,n);	%initialization vector for G1
L=2^n-1;

% G2j LFSR: x^10+x^9+x^8+x^6+x^3+x^2+1
t=[0 1 1 0 0 1 0 1 1 1];
q=ones(1,n);	%initialization vector for G2

% generate C/A Code sequences:
tap_sel=tap(sv,:);
for inc=1:L
    g2(:,inc)=mod(sum(q(tap_sel),2),2);
    g(:,inc)=mod(g1(n)+g2(:,inc),2);
   g1=[mod(sum(g1.*s),2) g1(1:n-1)];
   q=[mod(sum(q.*t),2) q(1:n-1)];
end

%upsample to desired rate
if fs~=1
	%fractional upsampling with zero order hold
	index=0;
	for cnt = 1/fs:1/fs:L
		index=index+1;
		if ceil(cnt) > L   %traps a floating point error in index
			gfs(:,index)=g(:,L);
		else
			gfs(:,index)=g(:,ceil(cnt));
		end
	end 
	g=gfs;
end