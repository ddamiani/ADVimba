TOP=../..
include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE

#----------------------------------------------------
#  Optimization of db files using dbst (DEFAULT: NO)
#DB_OPT = YES

DB += $(patsubst ../%, %, $(wildcard ../*.template))

DB += $(patsubst ../%, %, $(wildcard ../*.env))

REQ += vimba.req

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
