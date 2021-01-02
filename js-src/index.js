import ReactDOM from 'react-dom';
import React from 'react';
import MainController from './MainController';

window.addEventListener('load', () => {
	ReactDOM.render(
		<MainController />,
		document.getElementById('root'));
});