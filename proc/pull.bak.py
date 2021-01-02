import psycopg2 as pg
from queue import Queue, Empty
import functools
from pyrsistent import v as V
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
			hitQ.put((V(), V())) # for each prefix I need to get the total score of all the remaining possibiliies and the scores of each of those as well, then break those into grouped letter placements. These will likely be very big so I would want to put these into the database if I can
		# it's important to track the number of failures to get to that point too, so the state seems to be:
		# set of failed guesses
		# pos-letter combinations
		#
		# from a given guess, we split into all of the new positions and task them to count for each sub. But the distribution is just meant for making decisions on the next letter to choose: the actual probability of being wrong is given from the score distribution of the terms that don't have the next chosen letter. Note we have to recalculate the distributions updating the arrays separately, the hit array and the fail array: these are the two dimensions. And each node yields two outcomes, one for success and one for failure to the next most likely letter
		# That makes sense. To queue for BFS I may have to just be prudent in how I push into the queue, just to make sure I go along the failures before I go along the axis of successes. Also note that if I do want to just make conditional probabilities in the DB then I'll have to include the failure probabilities relative to the parent. And I guess the number of failures as well. Or I can just index them properly. Each stores the index relative to the parent letters, as well as the configuration? This is also unique, which makes it hard to store into a DB other than as a JSON object since it's a list of tuples. The BFS will be dominated by the last layer, I may just hold this in memory until I find a good way to represent it on disk, maybe even just as a flat JSON.
		# I need to know the probability of the match failing which happens if we choose something that doesn't contain the most likely letter, which is distinct from the score of the words with the most likely letter: I need to get the sum of the scores of all the words so I can do the universal difference/ratio
		while not (hitQ.empty() and failQ.empty()):
			try:
				q = failQ.get(timeout=0)
			except Empty:
				q = hitQ.get()
			
			hits, fails = q
			print(q)
			flat_hits = [s for hit in hits for s in hit]
			sys.stdout.write('Scoring\r')
			cur.execute('''
				SELECT COUNT(*), SUM(score) FROM words w
				LEFT JOIN letters l ON l.letter = ANY(%s) AND l.word = w.id
				WHERE l.word IS NULL
				''' + "".join([' AND w.l%s=%s'] * len(hits)),
				tuple([list(fails)] + flat_hits)
			)
			scorer = cur.fetchone()
			num, tot = scorer
			if num > 0:
				sys.stdout.write('Searching\r')
				cur.execute('''
					SELECT st1.letter, COUNT(*), SUM(st1.score) AS s FROM (
					  SELECT l3.letter, w.score, w.id 
					    FROM words w
					    LEFT JOIN letters l2 ON w.id = l2.word AND l2.letter = ANY(%s)
					    INNER JOIN letters l3 ON l3.word = w.id
							WHERE l2.word IS NULL AND l3.letter <> ALL(%s)
					'''\
					+ "".join([' AND w.l%s=%s'] * len(hits))\
					+ ''') st1
					GROUP BY st1.letter
					ORDER BY s DESC LIMIT 1''', # WHERE NOT (st1.letter ~ '[^A-Za-z]')
					tuple([list(fails), list(set(hit[1] for hit in hits))] + flat_hits)
				) # AND w.length = %s
				nextr = cur.fetchone()
				if nextr != None:
					(next_letter, next_count, score) = nextr
					sys.stdout.write('Assembling\r')
					cur.execute('''
						SELECT COUNT(*), l1.pos FROM words w
						LEFT JOIN letter_agg l ON l.letter = ANY(%s) AND l.word = w.id
						INNER JOIN letter_agg l1 ON l1.word = w.id
						WHERE l.letter IS NULL AND l1.letter = %s
						'''\
						+ "".join([' AND w.l%s=%s'] * len(hits))
						+ ' GROUP BY l1.pos',
						tuple([list(fails)] + [next_letter] + flat_hits)
					)
					nexts = cur.fetchall()
					json.dump([flat_hits, list(fails), scorer, nextr, nexts], outf, cls=DecimalEncoder)
					outf.write('\n')
					outf.flush()
					
					for n in nexts:
						hitQ.put((hits + [(n_, next_letter) for n_ in n[1] if n_ < 30], fails))
					failQ.put((hits, fails.append(next_letter)))
				# pdb.set_trace()
			
if __name__ == '__main__':
	run()