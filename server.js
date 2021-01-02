const express = require('express');
	const app = express();
const Q = require('q');
const { OrderedMap } = require('immutable');
const { pool } = require('./pg');

// const target = 'if only this damn application were easier to program, then i\'d be rolling in it alas too many cities';

const multer = require("multer")();
// app.use(bodyParser.urlencoded({ extended: false }));
app.use(multer.array());

app.use(express.static('public'));
app.listen(8081);

// DP
// psql.query('CREATE TEMPORARY TABLE tph (p VARCHAR(64), n SERIAL PRIMARY KEY);')
// 	.then(_ => psql.query('INSERT INTO tph VALUES %L', target.split(' ')))
// 	.then(_ => psql.query('SELECT * FROM tph'))

function rethrow(msg) {
	return e => { console.log(e); throw new Error(msg); };
}
app.post('/poll', (req, res) => {
	console.log(req.body);
	res.status(200).end();
	if(0) {
		const path = req.body.map(p => parseInt(p)).filter(p => !isNaN(p));
		pool.connect()
		    .then(psql => {
		    	return psql.query({
		    		text: `SELECT name, lat, lon, id FROM pl WHERE id IN ('${path.join('\',\'')}')`,
		    		rowMode: 'array'
		    	})
		    		.then(places => {
		    			const ret = []
		    			for(const p of path) {
		    				for(const r of places.rows) {
		    					if(p === r[3]) {
		    						ret.push(r);
		    						break;
		    					}
		    				}
		    			}
		    			res.send(ret);
		    			psql.release();
		    		}).catch(e => {
			 			console.log(e.message);
			 			res.status(501).send(e.message);
			 			psql.release();
			 		});
		    });
  }
});