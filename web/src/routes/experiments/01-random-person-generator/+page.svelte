<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	let personas = $state([]);
	let selectedPersona = $state(null);
	let loading = $state(false);
	let error = $state(null);
	let prompt = $state('');
	let showPrompt = $state(false);
	let models = $state([]);
	let selectedModel = $state('gpt-4o-mini');
	let map = null;
	let markers = [];

	const API_URL = 'http://localhost:8000';

	// Stop words to exclude from word frequency
	const STOP_WORDS = new Set([
		'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
		'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had',
		'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
		'shall', 'can', 'need', 'dare', 'ought', 'used', 'it', 'its', 'he', 'she', 'they',
		'them', 'their', 'his', 'her', 'him', 'who', 'whom', 'whose', 'which', 'what',
		'this', 'that', 'these', 'those', 'i', 'me', 'my', 'we', 'us', 'our', 'you', 'your',
		'also', 'just', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'such', 'no',
		'nor', 'not', 'now', 'then', 'there', 'here', 'when', 'where', 'why', 'how', 'all',
		'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'any', 'no', 'none',
		'one', 'two', 'three', 'first', 'second', 'new', 'old', 'high', 'low', 'into', 'over',
		'after', 'before', 'between', 'under', 'again', 'further', 'once', 'during', 'out',
		'up', 'down', 'off', 'about', 'above', 'below', 'being', 'having', 'doing', 'while'
	]);

	// Common activities/hobbies to look for in briefs
	const ACTIVITY_PATTERNS = [
		'reading', 'writing', 'cooking', 'baking', 'gardening', 'hiking', 'running',
		'cycling', 'swimming', 'yoga', 'meditation', 'painting', 'drawing', 'photography',
		'music', 'guitar', 'piano', 'singing', 'dancing', 'traveling', 'camping',
		'fishing', 'hunting', 'gaming', 'video games', 'chess', 'volunteering',
		'knitting', 'sewing', 'woodworking', 'crafts', 'pottery', 'blogging',
		'podcasting', 'movies', 'film', 'theater', 'sports', 'basketball', 'football',
		'soccer', 'tennis', 'golf', 'skiing', 'snowboarding', 'surfing', 'climbing',
		'martial arts', 'boxing', 'weightlifting', 'fitness', 'crossfit', 'pilates',
		'bird watching', 'astronomy', 'coding', 'programming', 'collecting', 'wine',
		'coffee', 'tea', 'beer', 'brewing', 'animals', 'pets', 'dogs', 'cats',
		'horses', 'nature', 'environment', 'activism', 'politics', 'history',
		'science', 'technology', 'fashion', 'shopping', 'art', 'museums', 'concerts',
		'festivals', 'food', 'restaurants', 'socializing', 'family', 'church',
		'community', 'teaching', 'mentoring', 'learning', 'languages'
	];

	function extractFirstName(fullName) {
		return fullName.split(' ')[0];
	}

	function extractActivities(brief) {
		const lowerBrief = brief.toLowerCase();
		const found = [];
		for (const activity of ACTIVITY_PATTERNS) {
			if (lowerBrief.includes(activity) && !found.includes(activity)) {
				found.push(activity);
			}
		}
		return found;
	}

	function extractWords(text) {
		return text
			.toLowerCase()
			.replace(/[^a-z\s]/g, '')
			.split(/\s+/)
			.filter(word => word.length > 2 && !STOP_WORDS.has(word));
	}

	// Computed stats
	let stats = $derived.by(() => {
		if (personas.length === 0) return null;

		const ages = personas.map((p) => p.age);
		const genderCounts = {};
		const occupationCounts = {};
		const continentCounts = {};
		const countryCounts = {};
		const educationCounts = {};
		const politicalCounts = {};
		const firstNameCounts = {};
		const activityCounts = {};
		const wordCounts = {};

		personas.forEach((p) => {
			const gender = p.gender || 'Unknown';
			const category = p.occupation_category || 'Unknown';
			const continent = p.continent || 'Unknown';
			const country = p.country || 'Unknown';
			const education = p.education || 'Unknown';
			const political = p.political_leaning || 'Unknown';
			const firstName = extractFirstName(p.name);
			const activities = extractActivities(p.brief || '');
			const words = extractWords(p.brief || '');

			genderCounts[gender] = (genderCounts[gender] || 0) + 1;
			occupationCounts[category] = (occupationCounts[category] || 0) + 1;
			continentCounts[continent] = (continentCounts[continent] || 0) + 1;
			countryCounts[country] = (countryCounts[country] || 0) + 1;
			educationCounts[education] = (educationCounts[education] || 0) + 1;
			politicalCounts[political] = (politicalCounts[political] || 0) + 1;
			firstNameCounts[firstName] = (firstNameCounts[firstName] || 0) + 1;

			activities.forEach(act => {
				activityCounts[act] = (activityCounts[act] || 0) + 1;
			});

			words.forEach(word => {
				wordCounts[word] = (wordCounts[word] || 0) + 1;
			});
		});

		// Age buckets
		const ageBuckets = { '18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '56-65': 0, '66+': 0 };
		ages.forEach((age) => {
			if (age <= 25) ageBuckets['18-25']++;
			else if (age <= 35) ageBuckets['26-35']++;
			else if (age <= 45) ageBuckets['36-45']++;
			else if (age <= 55) ageBuckets['46-55']++;
			else if (age <= 65) ageBuckets['56-65']++;
			else ageBuckets['66+']++;
		});

		// Get top 3 names
		const topNames = Object.entries(firstNameCounts)
			.sort((a, b) => b[1] - a[1])
			.slice(0, 3);

		// Get top 3 activities
		const topActivities = Object.entries(activityCounts)
			.sort((a, b) => b[1] - a[1])
			.slice(0, 3);

		// Get top 3 words
		const topWords = Object.entries(wordCounts)
			.sort((a, b) => b[1] - a[1])
			.slice(0, 3);

		return {
			total: personas.length,
			age: {
				min: Math.min(...ages),
				max: Math.max(...ages),
				avg: (ages.reduce((a, b) => a + b, 0) / ages.length).toFixed(1),
				buckets: ageBuckets
			},
			gender: genderCounts,
			occupation: occupationCounts,
			continent: continentCounts,
			countries: Object.keys(countryCounts).length,
			education: educationCounts,
			political: politicalCounts,
			topNames,
			topActivities,
			topWords
		};
	});

	onMount(async () => {
		if (!browser) return;

		document.body.classList.add('wide');

		// Fetch prompt and models in parallel
		try {
			const [promptRes, modelsRes] = await Promise.all([
				fetch(`${API_URL}/api/prompt`),
				fetch(`${API_URL}/api/models`)
			]);

			if (promptRes.ok) {
				const data = await promptRes.json();
				prompt = data.prompt;
			}

			if (modelsRes.ok) {
				const data = await modelsRes.json();
				models = data.models;
			}
		} catch (e) {
			console.log('Could not fetch from API - server may not be running');
		}

		const L = await import('leaflet');

		map = L.map('map').setView([20, 0], 2);

		L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			attribution: '&copy; OpenStreetMap contributors',
			maxZoom: 18
		}).addTo(map);

		return () => {
			document.body.classList.remove('wide');
		};
	});

	async function generatePerson() {
		loading = true;
		error = null;

		try {
			const response = await fetch(`${API_URL}/api/generate-persona`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ model: selectedModel })
			});

			if (!response.ok) {
				throw new Error(`API error: ${response.status}`);
			}

			const persona = await response.json();
			personas = [...personas, persona];

			if (map && browser) {
				const L = await import('leaflet');
				const marker = L.marker([persona.latitude, persona.longitude])
					.addTo(map)
					.bindPopup(`<strong>${persona.name}</strong><br>${persona.occupation}`);

				marker.on('click', () => {
					selectedPersona = persona;
				});

				markers.push(marker);
				map.setView([persona.latitude, persona.longitude], 4);
			}

			selectedPersona = persona;
		} catch (e) {
			error = e.message;
			console.error('Failed to generate persona:', e);
		} finally {
			loading = false;
		}
	}

	function clearAll() {
		personas = [];
		selectedPersona = null;
		markers.forEach((m) => m.remove());
		markers = [];
		if (map) {
			map.setView([20, 0], 2);
		}
	}

	function formatPercent(count, total) {
		return ((count / total) * 100).toFixed(0) + '%';
	}
</script>

<svelte:head>
	<title>01: Random person generator</title>
	<link
		rel="stylesheet"
		href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
		integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
		crossorigin=""
	/>
</svelte:head>

<nav class="nav">
	<a href="/">&larr; Back to experiments</a>
</nav>

<header class="header">
	<h1>Random person generator</h1>
	<p class="subtitle">Experiment 01</p>
</header>

<div class="intro">
	<p>
		Uses a minimal prompt to generate random people via LLM. A follow-up call classifies
		their occupation. Watch the stats to see what patterns and biases emerge.
	</p>
	<p>
		Whilst this makes for a fun drinking game, it demonstrates the perils of relying on
		LLMs too heavily for simulating randomised behaviour—real-world representative samples
		or curated persona datasets remain far more valuable.
	</p>
</div>

<div class="prompt-section">
	<button class="prompt-toggle" onclick={() => (showPrompt = !showPrompt)}>
		{showPrompt ? 'Hide' : 'Show'} the prompt
	</button>

	{#if showPrompt}
		<pre class="prompt-display">{prompt || 'Loading prompt...'}</pre>
	{/if}
</div>

<div class="controls">
	<div class="model-selector">
		<label for="model-select">Model:</label>
		<select id="model-select" bind:value={selectedModel}>
			{#each models as model}
				<option value={model.id}>{model.name} ({model.provider})</option>
			{/each}
			{#if models.length === 0}
				<option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
			{/if}
		</select>
	</div>

	<button onclick={generatePerson} disabled={loading}>
		{loading ? 'Generating...' : 'Generate a random person'}
	</button>

	{#if personas.length > 0}
		<button onclick={clearAll} class="secondary">Clear all ({personas.length})</button>
	{/if}
</div>

{#if error}
	<div class="error-box">
		<p class="error">Error: {error}</p>
		<p class="error-hint">
			Make sure the API server is running:<br />
			<code>uv run python -m centuria.api.server</code>
		</p>
	</div>
{/if}

<div id="map"></div>

<div class="content-grid">
	<div class="persona-section">
		<h2>Selected Person</h2>
		{#if selectedPersona}
			<div class="persona-card">
				<h3>{selectedPersona.name}</h3>
				<dl class="persona-details">
					<dt>Age</dt>
					<dd>{selectedPersona.age}</dd>

					<dt>Gender</dt>
					<dd>{selectedPersona.gender || '—'}</dd>

					<dt>Occupation</dt>
					<dd>{selectedPersona.occupation}</dd>

					<dt>Category</dt>
					<dd>{selectedPersona.occupation_category || '—'}</dd>

					<dt>Education</dt>
					<dd>{selectedPersona.education || '—'}</dd>

					<dt>Political</dt>
					<dd>{selectedPersona.political_leaning || '—'}</dd>

					<dt>Location</dt>
					<dd>{selectedPersona.location}</dd>

					<dt>Country</dt>
					<dd>{selectedPersona.country || '—'}</dd>

					<dt>Continent</dt>
					<dd>{selectedPersona.continent || '—'}</dd>
				</dl>
				<p class="persona-brief">{selectedPersona.brief}</p>
			</div>
		{:else}
			<p class="placeholder">Generate a person to see their details here.</p>
		{/if}
	</div>

	<div class="stats-section">
		<h2>Statistics</h2>
		{#if stats}
			<p class="stat-total">{stats.total} {stats.total === 1 ? 'person' : 'people'} generated</p>

			<div class="stat-row three-col">
				<div class="stat-group stat-small">
					<h3>Top Names</h3>
					{#if stats.topNames.length > 0}
						<ol class="top-list">
							{#each stats.topNames as [name, count]}
								<li>{name} <span class="count">({count})</span></li>
							{/each}
						</ol>
					{:else}
						<p class="placeholder-small">—</p>
					{/if}
				</div>

				<div class="stat-group stat-small">
					<h3>Top Activities</h3>
					{#if stats.topActivities.length > 0}
						<ol class="top-list">
							{#each stats.topActivities as [activity, count]}
								<li>{activity} <span class="count">({count})</span></li>
							{/each}
						</ol>
					{:else}
						<p class="placeholder-small">—</p>
					{/if}
				</div>

				<div class="stat-group stat-small">
					<h3>Top Words</h3>
					{#if stats.topWords.length > 0}
						<ol class="top-list">
							{#each stats.topWords as [word, count]}
								<li>{word} <span class="count">({count})</span></li>
							{/each}
						</ol>
					{:else}
						<p class="placeholder-small">—</p>
					{/if}
				</div>
			</div>

			<div class="stat-group">
				<h3>Age Distribution</h3>
				<p class="stat-summary">Range: {stats.age.min}–{stats.age.max} (avg: {stats.age.avg})</p>
				<div class="bar-chart">
					{#each Object.entries(stats.age.buckets) as [bucket, count]}
						<div class="bar-row">
							<span class="bar-label">{bucket}</span>
							<div class="bar-track">
								<div class="bar bar-age" style="width: {Math.max((count / stats.total) * 100, count > 0 ? 4 : 0)}%"></div>
							</div>
							<span class="bar-value">{count}</span>
						</div>
					{/each}
				</div>
			</div>

			<div class="stat-group">
				<h3>Gender</h3>
				<div class="bar-chart">
					{#each Object.entries(stats.gender).sort((a, b) => b[1] - a[1]) as [gender, count]}
						<div class="bar-row">
							<span class="bar-label">{gender}</span>
							<div class="bar-track">
								<div class="bar bar-gender" style="width: {(count / stats.total) * 100}%"></div>
							</div>
							<span class="bar-value">{count} <span class="bar-percent">({formatPercent(count, stats.total)})</span></span>
						</div>
					{/each}
				</div>
			</div>

			<div class="stat-group">
				<h3>Education</h3>
				<div class="bar-chart">
					{#each Object.entries(stats.education).sort((a, b) => b[1] - a[1]) as [edu, count]}
						<div class="bar-row">
							<span class="bar-label" title={edu}>{edu}</span>
							<div class="bar-track">
								<div class="bar bar-education" style="width: {(count / stats.total) * 100}%"></div>
							</div>
							<span class="bar-value">{count}</span>
						</div>
					{/each}
				</div>
			</div>

			<div class="stat-group">
				<h3>Political Leaning</h3>
				<div class="bar-chart">
					{#each Object.entries(stats.political).sort((a, b) => b[1] - a[1]) as [pol, count]}
						<div class="bar-row">
							<span class="bar-label" title={pol}>{pol}</span>
							<div class="bar-track">
								<div class="bar bar-political" style="width: {(count / stats.total) * 100}%"></div>
							</div>
							<span class="bar-value">{count}</span>
						</div>
					{/each}
				</div>
			</div>

			<div class="stat-group">
				<h3>Occupation Category</h3>
				<div class="bar-chart">
					{#each Object.entries(stats.occupation).sort((a, b) => b[1] - a[1]) as [category, count]}
						<div class="bar-row">
							<span class="bar-label" title={category}>{category}</span>
							<div class="bar-track">
								<div class="bar bar-occupation" style="width: {(count / stats.total) * 100}%"></div>
							</div>
							<span class="bar-value">{count}</span>
						</div>
					{/each}
				</div>
			</div>

			<div class="stat-group">
				<h3>Geography</h3>
				<p class="stat-summary">{stats.countries} {stats.countries === 1 ? 'country' : 'countries'}</p>
				<div class="bar-chart">
					{#each Object.entries(stats.continent).sort((a, b) => b[1] - a[1]) as [continent, count]}
						<div class="bar-row">
							<span class="bar-label">{continent}</span>
							<div class="bar-track">
								<div class="bar bar-geo" style="width: {(count / stats.total) * 100}%"></div>
							</div>
							<span class="bar-value">{count}</span>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<p class="placeholder">Statistics will appear as you generate people.</p>
		{/if}
	</div>
</div>

<style>
	.header {
		margin-bottom: 0.5rem;
	}

	.intro {
		margin-bottom: 1.5rem;
	}

	.intro p:last-child {
		margin-bottom: 0;
	}

	.prompt-section {
		margin-bottom: 1.5rem;
	}

	.prompt-toggle {
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
		padding: 0.4rem 0.8rem;
		font-size: 0.9rem;
		margin-top: 0;
	}

	.prompt-toggle:hover {
		background: var(--accent);
		color: white;
	}

	.prompt-display {
		background: #f5f5f5;
		border: 1px solid #ddd;
		border-radius: 4px;
		padding: 1rem 1.25rem;
		margin-top: 1rem;
		font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
		font-size: 0.8rem;
		line-height: 1.5;
		white-space: pre-wrap;
		overflow-x: auto;
		color: #444;
	}

	.controls {
		display: flex;
		gap: 1rem;
		flex-wrap: wrap;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.controls button {
		margin-top: 0;
		height: 2.5rem;
	}

	.model-selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.model-selector label {
		font-size: 0.9rem;
		color: #555;
	}

	.model-selector select {
		font-family: inherit;
		font-size: 1rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid #ccc;
		border-radius: 4px;
		background: white;
		cursor: pointer;
		height: 2.5rem;
		box-sizing: border-box;
	}

	.model-selector select:focus {
		outline: none;
		border-color: var(--accent);
	}

	.secondary {
		background: #666;
	}

	.error-box {
		background: #fff5f5;
		border: 1px solid #ffcccc;
		padding: 1rem 1.5rem;
		margin-bottom: 1.5rem;
		border-radius: 4px;
	}

	.error {
		color: #8b0000;
		margin-bottom: 0.5rem;
	}

	.error-hint {
		font-size: 0.9rem;
		color: #666;
		margin-bottom: 0;
	}

	.error-hint code {
		display: inline-block;
		background: #f0f0f0;
		padding: 0.3rem 0.6rem;
		border-radius: 3px;
		font-size: 0.85rem;
		margin-top: 0.5rem;
	}

	#map {
		height: 450px;
		width: 100%;
		margin-bottom: 2rem;
		border: 1px solid #ddd;
		border-radius: 4px;
	}

	.content-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 3rem;
		align-items: start;
	}

	.persona-section h2,
	.stats-section h2 {
		font-size: 1.2rem;
		margin-top: 0;
		margin-bottom: 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid #ddd;
	}

	.placeholder {
		color: #999;
		font-style: italic;
	}

	.placeholder-small {
		color: #999;
		font-style: italic;
		font-size: 0.9rem;
		margin: 0;
	}

	.persona-card {
		background: #fafafa;
		border-left: 3px solid var(--accent);
		padding: 1.5rem;
		margin: 0;
	}

	.persona-card h3 {
		font-size: 1.3rem;
		margin-bottom: 1rem;
	}

	.persona-details {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.4rem 1rem;
		margin-bottom: 1rem;
		font-size: 0.95rem;
	}

	.persona-details dt {
		color: #666;
	}

	.persona-details dd {
		margin: 0;
	}

	.persona-brief {
		font-style: italic;
		color: #555;
		border-top: 1px solid #e0e0e0;
		padding-top: 1rem;
		margin-bottom: 0;
		line-height: 1.6;
	}

	.stat-total {
		font-size: 1.1rem;
		font-weight: bold;
		color: var(--accent);
		margin-bottom: 1.5rem;
	}

	.stat-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
		margin-bottom: 1.5rem;
	}

	.stat-row.three-col {
		grid-template-columns: 1fr 1fr 1fr;
	}

	.stat-group {
		margin-bottom: 1.5rem;
	}

	.stat-small {
		margin-bottom: 0;
	}

	.stat-group h3 {
		font-size: 1rem;
		color: #444;
		margin-bottom: 0.5rem;
	}

	.top-list {
		margin: 0;
		padding-left: 1.25rem;
		font-size: 0.9rem;
	}

	.top-list li {
		margin-bottom: 0.25rem;
	}

	.top-list .count {
		color: #888;
	}

	.stat-summary {
		font-size: 0.9rem;
		color: #666;
		margin-bottom: 0.75rem;
	}

	.bar-chart {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.bar-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.bar-label {
		width: 100px;
		flex-shrink: 0;
		font-size: 0.85rem;
		color: #555;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.bar-track {
		flex: 1;
		height: 18px;
		background: #e8e8e8;
		border-radius: 3px;
		overflow: hidden;
	}

	.bar {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	.bar-age {
		background: #8b0000;
	}

	.bar-gender {
		background: #8b0000;
	}

	.bar-education {
		background: #6a1b9a;
	}

	.bar-political {
		background: #e65100;
	}

	.bar-occupation {
		background: #2e7d32;
	}

	.bar-geo {
		background: #1565c0;
	}

	.bar-value {
		width: 70px;
		flex-shrink: 0;
		font-size: 0.85rem;
		color: #555;
		text-align: right;
	}

	.bar-percent {
		color: #888;
	}

	@media (max-width: 900px) {
		.content-grid {
			grid-template-columns: 1fr;
			gap: 2rem;
		}

		.stat-row {
			grid-template-columns: 1fr;
			gap: 1rem;
		}

		.stat-row.three-col {
			grid-template-columns: 1fr;
		}
	}
</style>
