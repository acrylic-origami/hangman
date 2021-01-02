import React from 'react'
import { Map, Set, List } from 'immutable'

function range(n) {
	return [...Array(n).keys()];
}
function get_fails(state_) {
	return Set(state_.guesses.skipLast(1)).subtract(state_.hits.flatten());
}
const PHRASES = ['Hmm, how about ', 'Do you have ', 'What about ', 'Is there a[n] ']
export default class extends React.Component {
	constructor(props) {
		super(props);
		this.state = {
			ls: null,
			hits: null,
			guesses: null,
			editing: false,
			txid: 0,
			rxid: 0
		};
	}
	handleManualEdit = (e) => {
		const v = e.target.value.toLowerCase();
		const targ = e.target.id.slice('charmap_'.length).split('-').map(i => parseInt(i));
		this.setState(({ hits, guesses }) => {
			if(guesses.includes(v) || v === '') {
				return { hits: hits.update(targ[0], l => l.set(targ[1], v)) };
			}
		})
	}
	handleManualToggle = (e) => {
		this.setState(({ editing }) => ({ editing: !editing }));
	}
	handlePlacement = (e) => {
		const v = e.target.value;
		if(!this.state.editing && this.state.guesses.size > 0 && (v === '' || v === this.state.guesses.last())) {
			const targ = e.target.id.slice('charmap_'.length).split('-').map(i => parseInt(i));
			
			this.setState(({ hits, guesses }) => ({
				hits: hits.update(targ[0], l => l.set(targ[1], v === '' ? guesses.last() : ''))
			}));
		}
	}
	handlePollSubmit = (e) => {
		if(e !== null) {
			e.preventDefault();
			e.stopPropagation();
		}
		const F = new FormData();
		F.set('guesses', JSON.stringify(this.state.guesses.toArray()));
		F.set('hits', JSON.stringify(this.state.hits.map(l => l.map((l_, i) => [i + 1, l_]).filter(([i, l_]) => l_ !== '').toArray()).toArray()));
		F.set('ls', JSON.stringify(this.state.ls))
		this.setState(({ txid }) => ({ txid: txid + 1 }));
		fetch('api/poll', { method: 'POST', body: F, mode: 'cors' })
			.then(r => r.json())
			.then(J =>
				this.setState(({ rxid, txid, guesses }) => ({
					rxid: rxid + 1,
					guesses: guesses.push(J['next'])
				}))
			);
		return false;
	}
	handleBlockSubmit = (e) => {
		e.preventDefault();
		e.stopPropagation();
		const blocks = e.target.blocks.value.split(',').map(i => parseInt(i));
		if(!blocks.some(b => isNaN(b))) {
			this.setState(({ txid }) => ({
				ls: blocks,
				hits: List(range(blocks.length)).map((_, i) => List(range(blocks[i])).map(_ => '')),
				guesses: List()
			}), _ => {
				this.handlePollSubmit(null);
			});
		}
		return false;
	}
	render = () => <div id="main_content">
			{ (this.state.ls === null || this.state.hits === null || this.state.guesses === null)
				? <section>
					<form action="." onSubmit={this.handleBlockSubmit} id="block_form">
						<label htmlFor="block_entry" id="block_label">Enter word lengths (e.g. 'try this' -> '3,4'):</label><input type="text" name="blocks" id="block_entry" />
						<input type="submit" className="hide" />
					</form>
					</section>
				: <section>
					<form action='.' onSubmit={this.handlePollSubmit}>
						<div>
							<h3>Fails:</h3>
							<ul id="fails">
								<li>&nbsp;</li>
								{get_fails(this.state).sort().map((f, i) => <li key={f}>{f}</li>)}
							</ul>
						</div>
						<h2>AI guesses:</h2>
						<div id="guess_container">
							{this.state.rxid >= this.state.txid
							? <h3>{ this.state.guesses.last() }</h3>
							: <span><h3>&nbsp;</h3><span className="spinner"></span></span>}
						</div>
						<ul>
							{ this.state.ls.map((l, i) =>
								<li key={i}>
									<ul>
										{range(l).map((j, j_) => {
											const letter = this.state.hits.get(i).get(j); 
											return <li key={j_}>
												<input
													type="text"
													maxLength={1} 
													value={letter}
													id={`charmap_${i}-${j}`} 
													onInput={this.handleManualEdit}
													onClick={this.handlePlacement}
													readOnly={!this.state.editing} 
													className={`charmap ${
														letter === this.state.guesses.last()
															? 'latest'
															: ''
													}`}
													key={`${i},${j}`} />
											</li>
										})}
									</ul>
								</li>
							) }
						</ul>
						<input type="button" onClick={this.handleManualToggle} value={ this.state.editing ? 'Stop editing' : 'Edit entries' } />
						<input type="submit" value="Next guess" />
					</form>
				</section>
			}
		</div>
}