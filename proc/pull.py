import psycopg2 as pg
from random import randint
from queue import Queue, Empty
import functools
from pyrsistent import v as V, m as M
import pdb
import decimal
import json
import sys

class DecimalEncoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, decimal.Decimal):
			return float(o)
		return super(DecimalEncoder, self).default(o)


def run():
	with pg.connect('dbname=ng_am user=ng_am password=ng_am') as conn, open('out', 'w') as outf:
		cur = conn.cursor()
		hitQ = Queue()
		failQ = Queue()
		try:
			with open('qs.json', 'r') as qf:
				[hitL, failL] = json.load(qf)
				for hit in hitL:
					hitQ.put((V(*[tuple(h) for h in hit[0] if h[0] < 30]), V(*hit[1])))
				for fail in failL:
					failQ.put(fail)
		except FileNotFoundError:
			pass
			
		if hitQ.qsize() == 0:
			hitQ.put((M(), V())) # for each prefix I need to get the total score of all the remaining possibiliies and the scores of each of those as well, then break those into grouped letter placements. These will likely be very big so I would want to put these into the database if I can
		# it's important to track the number of failures to get to that point too, so the state seems to be:
		# set of failed guesses
		# pos-letter combinations
		#
		# from a given guess, we split into all of the new positions and task them to count for each sub. But the distribution is just meant for making decisions on the next letter to choose: the actual probability of being wrong is given from the score distribution of the terms that don't have the next chosen letter. Note we have to recalculate the distributions updating the arrays separately, the hit array and the fail array: these are the two dimensions. And each node yields two outcomes, one for success and one for failure to the next most likely letter
		# That makes sense. To queue for BFS I may have to just be prudent in how I push into the queue, just to make sure I go along the failures before I go along the axis of successes. Also note that if I do want to just make conditional probabilities in the DB then I'll have to include the failure probabilities relative to the parent. And I guess the number of failures as well. Or I can just index them properly. Each stores the index relative to the parent letter_agg, as well as the configuration? This is also unique, which makes it hard to store into a DB other than as a JSON object since it's a list of tuples. The BFS will be dominated by the last layer, I may just hold this in memory until I find a good way to represent it on disk, maybe even just as a flat JSON.
		# I need to know the probability of the match failing which happens if we choose something that doesn't contain the most likely letter, which is distinct from the score of the words with the most likely letter: I need to get the sum of the scores of all the words so I can do the universal difference/ratio
		Q = [(M(), V())]
		# Q = [(M(e=[3], r=[5]), V('t'))]
		while len(Q) > 0:
			q = Q.pop(randint(0, len(Q) - 1))
			hits, fails = q
			print(q)
			flat_hits = [h_ for h in hits.items() for h_ in h] # (h[0], list(h[1]))
			num_hits = len(flat_hits) // 2
			hitset = list(hits.keys())
			sys.stdout.write('Scoring\r')
			cur.execute('''
				SELECT COUNT(*), SUM(score) FROM wordwide w
				''' + # "".join([' INNER JOIN letter_agg lhit%d ON lhit%d.letter = %%s AND lhit%d.pos = %%s AND lhit%d.word = w.id' % (i, i, i, i) for i in range(len(hits))])
				'''
				WHERE NOT (w.wa && %s :: CHAR(1)[])'''
				+ "".join([' AND w.n%s=%%s' % h[0] for h in hits.keys()]),
				tuple([list(fails)] + list(hits.values()))
			)
			scorer = cur.fetchone()
			num, tot = scorer
			if num > 0:
				sys.stdout.write('Searching\r')
				cur.execute('''
					SELECT st1.letter, COUNT(*), SUM(st1.score) AS s FROM (
					  SELECT l0.letter, w.score, w.id 
					    FROM wordwide w
				''' + # "".join([' INNER JOIN letter_agg lhit%d ON lhit%d.letter = %%s AND lhit%d.pos = %%s AND lhit%d.word = w.id' % (i, i, i, i) for i in range(len(hits))]) +
				''' INNER JOIN letter_agg l0 ON l0.word = w.id
						WHERE l0.letter <> ALL(%s) AND NOT (w.wa && %s :: CHAR(1)[])
				''' + "".join([' AND w.n%s=%%s' % h[0] for h in hits.keys()]) +
				''') st1
					GROUP BY st1.letter
					ORDER BY s DESC LIMIT 1''', # WHERE NOT (st1.letter ~ '[^A-Za-z]')
					tuple([hitset, list(fails)] + list(hits.values()))
				) # AND w.length = %s
				nextr = cur.fetchone()
				if nextr != None:
					(next_letter, next_count, score) = nextr
					sys.stdout.write('Assembling\r')
					cur.execute('''
						SELECT COUNT(*), l1.pos FROM wordwide w
						INNER JOIN letter_agg l1 ON l1.word = w.id
						''' + # "".join([' INNER JOIN letter_agg lhit%d ON lhit%d.letter = %%s AND lhit%d.pos = %%s AND lhit%d.word = w.id' % (i, i, i, i) for i in range(len(hits))]) +
						'''
						WHERE l1.letter = %s AND NOT (w.wa && %s :: CHAR(1)[])
						''' + "".join([' AND w.n%s=%%s' % h for h in hits.keys()]) +
						'''
						GROUP BY l1.pos
						''',
						tuple([next_letter, list(fails)] + list(hits.values()))
					)
					nexts = cur.fetchall()
					json.dump([flat_hits, list(fails), scorer, nextr, nexts], outf, cls=DecimalEncoder)
					outf.write('\n')
					outf.flush()
					
					for n in nexts:
						Q.append((hits.set(next_letter, n[1]), fails))
					Q.append((hits, fails.append(next_letter)))
				# pdb.set_trace()
			
if __name__ == '__main__':
	run()