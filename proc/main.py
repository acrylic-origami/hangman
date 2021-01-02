import csv
import os
import sys
# import psycopg2
import glob

def run():
	fs = glob.glob(sys.argv[1])
	i = 0
	with open('out_words.csv', 'w') as h: # open('out_score.csv', 'w') as g, 
		E = csv.writer(h, quotechar='"')
		# D = csv.writer(g, quotechar='"')
		last = None
		s = 0
		for fn in fs:
			with open(fn, 'r') as f:
				C = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE)
				for l in C:
					if last != l[0]:
						if last != None:
							E.writerow([i, last, s])
						last = l[0]
						s = 0
						i += 1
					s += sum([(int(s__[1]) * 10) // (2010 - int(s__[0])) for s_ in l[3:] for s__ in [s_.split(',')]])
					
					# l_ = l[3:]
					# if len(l_) > 5:
					# 	l_ = l_[-5:]
						
					# for m in l_:
					# 	r = [i]
					# 	if ',' in m:
					# 		[m, b] = m.split(',')
					# 		r.append(int(b))
					# 	r.append(int(m))
					# 	D.writerow(r)

run()