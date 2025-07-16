import argparse
import sys
import os

# experiment code list
# 1. {two flow}-{line rate start}
# 2. {start and exit}-{3 flows}-{additional flow start at 3s exit at 5s} 2
# 3. {convergence in dc}-{2s-9s}-{4 flows}

config_template="""ENABLE_QCN 1
USE_DYNAMIC_PFC_THRESHOLD 1

PACKET_PAYLOAD_SIZE 1000

TOPOLOGY_FILE mix/{topo}.txt
FLOW_FILE mix/{trace}.txt
TRACE_FILE mix/trace.txt
TRACE_OUTPUT_FILE ./results/trace/{out_name}.txt
FCT_OUTPUT_FILE ./results/fct/{out_name}.txt
PFC_OUTPUT_FILE ./results/pfc/{out_name}.txt

SIMULATOR_STOP_TIME {simulation_time}

EXP_CODE {exp_code}

CC_MODE {mode}
ALPHA_RESUME_INTERVAL {t_alpha}
RATE_DECREASE_INTERVAL {t_dec}
CLAMP_TARGET_RATE 0
RP_TIMER {t_inc}
EWMA_GAIN {g}
FAST_RECOVERY_TIMES 1
RATE_AI {ai}Mb/s
RATE_HAI {hai}Mb/s
MIN_RATE 1000Mb/s
DCTCP_RATE_AI {dctcp_ai}Mb/s

ERROR_RATE_PER_LINK 0.0000
L2_CHUNK_SIZE 4000
L2_ACK_INTERVAL 1
L2_BACK_TO_ZERO 0

HAS_WIN {has_win}
GLOBAL_T 0
VAR_WIN {vwin}
FAST_REACT {us}
U_TARGET {u_tgt}
MI_THRESH {mi}
INT_MULTI {int_multi}
MULTI_RATE 0
SAMPLE_FEEDBACK 0
PINT_LOG_BASE {pint_log_base}
PINT_PROB {pint_prob}

RATE_BOUND 1

ACK_HIGH_PRIO {ack_prio}

LINK_DOWN {link_down}

ENABLE_TRACE {enable_tr}

KMAX_MAP {kmax_map}
KMIN_MAP {kmin_map}
PMAX_MAP {pmax_map}
BUFFER_SIZE {buffer_size}
QLEN_MON_FILE ./results/qlen/{out_name}.txt
QLEN_MON_START 2000000000
QLEN_MON_END 3000000000

POSEIDON_M {poseidon_m}
POSEIDON_MIN_RATE {poseidon_min_rate}
POSEIDON_MAX_RATE {poseidon_max_rate}
POSEIDON_MD_STRATEGY {poseidon_md_strategy}
"""
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='run simulation')
	parser.add_argument('--cc', dest='cc', action='store', default='poseidon', help="poseidon/hp/dcqcn/timely/dctcp/hpccPint")
	parser.add_argument('--trace', dest='trace', action='store', default='flow', help="the name of the flow file")
	parser.add_argument('--bw', dest="bw", action='store', default='50', help="the NIC bandwidth")
	parser.add_argument('--down', dest='down', action='store', default='0 0 0', help="link down event")
	parser.add_argument('--topo', dest='topo', action='store', default='fat', help="the name of the topology file")
	parser.add_argument('--utgt', dest='utgt', action='store', type=int, default=95, help="eta of HPCC")
	parser.add_argument('--mi', dest='mi', action='store', type=int, default=0, help="MI_THRESH")
	parser.add_argument('--hpai', dest='hpai', action='store', type=int, default=0, help="AI for HPCC")
	parser.add_argument('--pint_log_base', dest='pint_log_base', action = 'store', type=float, default=1.01, help="PINT's log_base")
	parser.add_argument('--pint_prob', dest='pint_prob', action = 'store', type=float, default=1.0, help="PINT's sampling probability")
	parser.add_argument('--enable_tr', dest='enable_tr', action = 'store', type=int, default=0, help="enable packet-level events dump")
	parser.add_argument('--poseidon_m', dest='poseidon_m', action = 'store', type=float, default=0.01, help="Poseidon's parameter m")
	parser.add_argument('--poseidon_min_rate', dest='poseidon_min_rate', action = 'store', type=float, default=0.1, help="Poseidon's min rate")
	parser.add_argument('--poseidon_md_strategy', dest='poseidon_md_strategy', action = 'store', default='ack', help="Poseidon's md strategy per ack or per rtt")
	parser.add_argument('--simulation_time', dest='simulation_time', action = 'store', type=float, default=2.05, help="The end time of this simulation")
	parser.add_argument('--exp_code', dest='exp_code', action = 'store', type=int, default=0, help="The experiment type of this simulation")
	parser.add_argument('--out_name', dest='out_name', action = 'store', default='', help="The output filename")
	parser.add_argument('--has_win', dest='has_win', action = 'store',type=int, default = 1, help="Bound the inflight bytes")
	args = parser.parse_args()

	topo=args.topo
	bw = int(args.bw)
	trace = args.trace
	#bfsz = 16 if bw==50 else 32
	bfsz = 16 * bw / 50
	u_tgt=args.utgt/100.
	mi=args.mi
	pint_log_base=args.pint_log_base
	pint_prob = args.pint_prob
	enable_tr = args.enable_tr
	poseidon_m = args.poseidon_m
	poseidon_min_rate = args.poseidon_min_rate  * 1000000000.0
	poseidon_max_rate = float(bw) * 1000000000.0
	poseidon_md_strategy = args.poseidon_md_strategy
	simulation_time = args.simulation_time
	exp_code = args.exp_code
	has_win = args.has_win
	out_name = args.out_name
	if out_name == '':
		print("must have out_name arg")
		sys.exit(1)
	

	failure = ''
	if args.down != '0 0 0':
		failure = '_down'

	config_name = "mix/gen/config_%s.txt"%(out_name)

	kmax_map = "2 %d %d %d %d"%(bw*1000000000, 400*bw/25, bw*4*1000000000, 400*bw*4/25)
	kmin_map = "2 %d %d %d %d"%(bw*1000000000, 100*bw/25, bw*4*1000000000, 100*bw*4/25)
	pmax_map = "2 %d %.2f %d %.2f"%(bw*1000000000, 0.2, bw*4*1000000000, 0.2)
	if (args.cc.startswith("dcqcn")):
		ai = 5 * bw / 25
		hai = 50 * bw /25

		if args.cc == "dcqcn":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
		elif args.cc == "dcqcn_paper":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=50, t_dec=50, t_inc=55, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
		elif args.cc == "dcqcn_vwin":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
		elif args.cc == "dcqcn_paper_vwin":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=50, t_dec=50, t_inc=55, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "hp":
		ai = 10 * bw / 25;
		if args.hpai > 0:
			ai = args.hpai
		hai = ai # useless
		int_multi = bw / 25;
		cc = "%s%d"%(args.cc, args.utgt)
		if (mi > 0):
			cc += "mi%d"%mi
		if args.hpai > 0:
			cc += "ai%d"%ai
		config_name = "mix/gen/config_%s_%s_%s%s.txt"%(topo, trace, cc, failure)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=cc, mode=3, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=1, u_tgt=u_tgt, mi=mi, int_multi=int_multi, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "poseidon":
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=11, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=1, hai=1, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=1, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "dctcp":
		ai = 10 # ai is useless for dctcp
		hai = ai  # also useless
		dctcp_ai=615 # calculated from RTT=13us and MTU=1KB, because DCTCP add 1 MTU per RTT.
		kmax_map = "2 %d %d %d %d"%(bw*1000000000, 30*bw/10, bw*4*1000000000, 30*bw*4/10)
		kmin_map = "2 %d %d %d %d"%(bw*1000000000, 30*bw/10, bw*4*1000000000, 30*bw*4/10)
		pmax_map = "2 %d %.2f %d %.2f"%(bw*1000000000, 1.0, bw*4*1000000000, 1.0)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=8, t_alpha=1, t_dec=4, t_inc=300, g=0.0625, ai=ai, hai=hai, dctcp_ai=dctcp_ai, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "timely":
		ai = 10 * bw / 10;
		hai = 50 * bw / 10;
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=7, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "timely_vwin":
		ai = 10 * bw / 10;
		hai = 50 * bw / 10;
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=7, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	elif args.cc == "hpccPint":
		ai = 10 * bw / 25;
		if args.hpai > 0:
			ai = args.hpai
		hai = ai # useless
		int_multi = bw / 25;
		cc = "%s%d"%(args.cc, args.utgt)
		if (mi > 0):
			cc += "mi%d"%mi
		if args.hpai > 0:
			cc += "ai%d"%ai
		cc += "log%.3f"%pint_log_base
		cc += "p%.3f"%pint_prob
		config_name = "mix/gen/config_%s_%s_%s%s.txt"%(topo, trace, cc, failure)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=cc, mode=10, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=has_win, vwin=has_win, us=1, u_tgt=u_tgt, mi=mi, int_multi=int_multi, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr, poseidon_m=poseidon_m, poseidon_min_rate=poseidon_min_rate, poseidon_max_rate=poseidon_max_rate, simulation_time=simulation_time, poseidon_md_strategy=poseidon_md_strategy, exp_code=exp_code, out_name=out_name)
	else:
		print("unknown cc:", args.cc)
		sys.exit(1)

	with open(config_name, "w") as file:
		file.write(config)
	
	os.system("./waf --run 'scratch/third %s' > ./results/data/%s.txt" % (config_name, out_name))
