;hC.cp

;version: 1.0/ TS3.2 /2013/06/17

;written for BioToolkit: JOS WTF 10.5.2013
;double-checked: VEDA SEWE July 2013

;basic cp experiment

;Avance II / AVIII version
;parameters:
;p1      : C 90 at pl1(acqt0-calculation & -DC90)
;p3      : H 90 at pl2
;p15     : HC CP at sp41 (f1,C) and sp40 (f2,H)
;pl1     : C pulse power
;pl2     : H pulse power
;pl12    : H dec power
;sp40    : H CP power
;sp41    : C CP power
;d1      : recycle delay; 1 to 5 times T1
;pcpd2   : pulse length in decoupling sequence cpdprg2
;cpdprg2 : spinal64, swftppm, tppm etc. decoupling program
;spnam40 : H ramp use e.g. ramp.10070 for variable amplitude CP
;spnam41 : C ramp use e.g. square.100 for square pulse CP 
;ZGOPTNS : -DC90 : optimize C 90 power
;          -Dlacq : aq is longer than 50 ms
;          or blank

;###############################################################
;#                                                             #
;#  H-C Cross Polarization Experiment                          #
;#                                                             #
;#  Adjust sp40, sp41, and p15 for maximum signal.             #
;#  The Hartman-Hahn CP condidition is B1(H)=B1(C)+-1          #
;#  sp40: usually a linear or tangenial amplitude ramped pulse #
;#  sp41: usually a rectangular constant amplitude pulse       #
;#  p15: usually between 500-2000 us (sample-dependent)        #
;#                                                             #
;###############################################################


;$COMMENT= HC CP
;$CLASS=BioSolids
;$DIM=1D
;$TYPE=CPMAS
;$SUBTYPE=Setup


prosol relations=<biosolCHN>

#include <CHN_defs.incl> 
        ; defines which channel corresponds to which nucleus
#include <trigg.incl>
        ; definition of external trigger output

define delay ONTIME
"ONTIME=aq+p15"

"acqt0=-(p1*2/3.1416)-1u"

                            ;##########################
;$EXTERN                    ;# Python insertion point #
                            ;##########################

Prepare, ze

;######################################################
;#               Protections: Pre-Check               #
;######################################################

ONTIME

#ifndef lacq
#include <acq_prot.incl>
        ;Max. 50 ms acquisition time
#include <ONTIME_prot.incl>
        ;total RF deposition restriction
#endif

#include <p15bio_prot.incl>
        ;p15 max. 10 ms

;######################################################
;#           Start of Active Pulse Program            #
;######################################################

Start, 30m do:H
  d1

  trigg
  1u fq=0.0:H                     ;set 1H on resonance

  (p3 pl2 ph1):H
  (p15:sp41 ph2):C  (p15:sp40 ph0):H
  (1u pl12):H

#ifdef C90 
  (p1 pl1 ph3):C  
#endif                                 /*end of C90*/ 

  1u cpds2:H

;#######################################################
;#                     Acquisition                     #
;#######################################################

  go=Start ph31
  1m do:H
  30m mc #0 to Start F0(zd)

HaltAcqu, 1m
Exit, exit

;#####################################
;#             Phase Cycle           #
;#####################################

ph0 = 0                ; H CP spin lock
ph1 = 1 3              ; H hard pulse
ph2 = 0 0 2 2 1 1 3 3  ; C CP spin lock 

#ifdef C90 
ph3 = 1 1 3 3 2 2 0 0  ; C hard pulse
#endif                    /*end of C90*/ 

ph31= 0 2 2 0 1 3 3 1  ; receiver

;#######################################################



;$Id:$
