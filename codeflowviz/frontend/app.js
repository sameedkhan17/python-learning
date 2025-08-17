const q = (s) => document.querySelector(s);
const btnAnalyze = q('#btnAnalyze');
const btnSample = q('#btnSample');
const taCode = q('#code');
const useGemini = q('#useGemini');
const preClean = q('#cleanCode');
const ulDiag = q('#diagnostics');
let cy;

function initCy() {
	cy = cytoscape({
		container: document.getElementById('cy'),
		style: [
			{ selector: 'node', style: {
				'background-color': '#7c5cff',
				'label': 'data(label)',
				'color': '#f1f5f9',
				'font-size': 12,
				'text-valign': 'center',
				'text-halign': 'center',
				'width': 'mapData(type, "var", 28, 48)',
				'height': 'mapData(type, "var", 28, 48)',
				'shape': 'data(typeShape)'
			}},
			{ selector: 'edge', style: {
				'width': 2,
				'line-color': '#2a3560',
				'target-arrow-color': '#2a3560',
				'target-arrow-shape': 'triangle',
				'curve-style': 'bezier',
				'label': 'data(label)',
				'font-size': 10,
				'color': '#9ea7b3',
				'text-background-color': '#0b1020',
				'text-background-opacity': 0.6,
				'text-background-shape': 'roundrectangle',
				'text-background-padding': 2
			}}
		],
		layout: { name: 'cose', animate: false }
	});
}

function elsFromGraph(graph) {
	const nodes = (graph.nodes || []).map(n => {
		const type = n.data.type || 'stmt';
		let typeShape = 'round-rectangle';
		if (type === 'var') typeShape = 'ellipse';
		if (type === 'function') typeShape = 'round-rectangle';
		if (type === 'class') typeShape = 'rectangle';
		if (type === 'if' || type === 'while' || type === 'for') typeShape = 'diamond';
		return { data: { ...n.data, typeShape } };
	});
	const edges = (graph.edges || []).map(e => ({ data: e.data }));
	return [...nodes, ...edges];
}

async function analyze() {
	btnAnalyze.disabled = true;
	btnAnalyze.textContent = 'Analyzing...';
	ulDiag.innerHTML = '';
	preClean.textContent = '';
	try {
		const resp = await fetch('/api/analyze', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ code: taCode.value, use_gemini: useGemini.checked })
		});
		if (!resp.ok) {
			throw new Error('Failed: ' + resp.status);
		}
		const data = await resp.json();
		preClean.textContent = data.clean_code || '';
		(data.diagnostics || []).forEach(d => {
			const li = document.createElement('li');
			li.textContent = d;
			ulDiag.appendChild(li);
		});
		cy.elements().remove();
		cy.add(elsFromGraph(data.graph || { nodes: [], edges: [] }));
		cy.layout({ name: 'cose', animate: false }).run();
	} catch (e) {
		const li = document.createElement('li');
		li.textContent = e.message || String(e);
		ulDiag.appendChild(li);
	} finally {
		btnAnalyze.disabled = false;
		btnAnalyze.textContent = 'Analyze';
	}
}

async function loadSample() {
	const resp = await fetch('/api/sample');
	if (resp.ok) {
		const data = await resp.json();
		taCode.value = data.code || '';
	}
}

window.addEventListener('DOMContentLoaded', () => {
	initCy();
	btnAnalyze.addEventListener('click', analyze);
	btnSample.addEventListener('click', loadSample);
});