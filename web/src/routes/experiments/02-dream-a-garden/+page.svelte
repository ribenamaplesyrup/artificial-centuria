<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	const API_URL = 'http://localhost:8000';

	// State
	let personas = $state([]);
	let loadingPersonas = $state(true);
	let error = $state(null);
	let models = $state([]);
	let selectedModel = $state('gpt-4o-mini');

	// Survey state
	let phase = $state('intro'); // intro, estimate, surveying, results, followup-estimate, followup-surveying, followup-results
	let surveyProgress = $state(0);
	let surveyResults = $state([]);
	let totalCost = $state(0);
	let costEstimate = $state(null);

	// Follow-up survey state
	let followUpQuestions = $state([]);
	let followUpResults = $state([]);
	let followUpCostEstimate = $state(null);
	let currentFollowUpQuestion = $state(0);
	let winningOption = $state(null);

	// Image generation state
	let generatedImage = $state(null);
	let imagePrompt = $state(null);
	let generatingImage = $state(false);
	let imageError = $state(null);

	// 30 possible uses for the garden space
	const gardenOptions = [
		// Food Production
		'Community vegetable garden with shared plots',
		'Traditional allotments for individual households',
		'Community orchard with fruit trees',
		'Herb and medicinal plant garden',
		'Urban farm with raised beds and composting',

		// Nature & Wildlife
		'Wildflower meadow for pollinators',
		'Native woodland with walking paths',
		'Wildlife pond and wetland habitat',
		'Butterfly and bee sanctuary',
		'Rewilded space with minimal intervention',

		// Recreation & Play
		"Children's adventure playground",
		'Multi-use games area (MUGA)',
		'Outdoor gym and fitness equipment',
		'Quiet seating area with benches',
		'Picnic lawn and BBQ area',

		// Community Spaces
		'Covered community pavilion for events',
		'Outdoor amphitheatre for performances',
		'Community kitchen garden with cooking area',
		'Flexible event space with power and lighting',
		'Outdoor cinema and gathering space',

		// Wellbeing & Therapy
		'Sensory garden for accessibility',
		'Meditation and mindfulness garden',
		'Therapeutic horticulture space',
		"Quiet contemplation garden (memorial/reflection)",
		'Forest bathing and nature connection area',

		// Practical & Sustainable
		'Secure bike parking and repair station',
		'Tool library and community workshop',
		'Rainwater harvesting and sustainable drainage',
		'Solar-powered community charging hub',
		'Mixed-use space with rotating seasonal uses'
	];

	// Computed: vote tallies
	let voteTallies = $derived.by(() => {
		if (surveyResults.length === 0) return [];

		const counts = {};
		gardenOptions.forEach((opt) => (counts[opt] = 0));

		surveyResults.forEach((r) => {
			// Find the best matching option
			const response = r.response.toLowerCase().trim();
			let matched = false;

			for (const opt of gardenOptions) {
				if (response.includes(opt.toLowerCase()) || opt.toLowerCase().includes(response)) {
					counts[opt]++;
					matched = true;
					break;
				}
			}

			// Fuzzy matching - check if any option words are in the response
			if (!matched) {
				for (const opt of gardenOptions) {
					const optWords = opt.toLowerCase().split(' ');
					const responseWords = response.split(' ');
					const overlap = optWords.filter((w) => responseWords.some((rw) => rw.includes(w) || w.includes(rw)));
					if (overlap.length >= 3) {
						counts[opt]++;
						matched = true;
						break;
					}
				}
			}

			// If still no match, count as "other"
			if (!matched) {
				counts['Other'] = (counts['Other'] || 0) + 1;
			}
		});

		return Object.entries(counts)
			.filter(([_, count]) => count > 0)
			.sort((a, b) => b[1] - a[1]);
	});

	// Computed: demographics breakdown of top choice voters
	let topChoiceVoters = $derived.by(() => {
		if (voteTallies.length === 0) return [];

		const topChoice = voteTallies[0]?.[0];
		if (!topChoice) return [];

		return surveyResults
			.filter((r) => {
				const response = r.response.toLowerCase();
				return response.includes(topChoice.toLowerCase()) || topChoice.toLowerCase().includes(response);
			})
			.map((r) => {
				const persona = personas.find((p) => p.id === r.persona_id);
				return persona ? { ...r, persona } : r;
			});
	});

	// Follow-up results tallies
	let followUpTallies = $derived.by(() => {
		if (followUpResults.length === 0 || followUpQuestions.length === 0) return [];

		return followUpQuestions.map((q, i) => {
			const questionResults = followUpResults.filter((r) => r.question_index === i);
			const counts = {};
			q.options.forEach((opt) => (counts[opt] = 0));

			questionResults.forEach((r) => {
				const response = r.response.toLowerCase().trim();
				for (const opt of q.options) {
					if (response.includes(opt.toLowerCase()) || opt.toLowerCase().includes(response)) {
						counts[opt]++;
						break;
					}
				}
			});

			return {
				question: q.text,
				tallies: Object.entries(counts).sort((a, b) => b[1] - a[1])
			};
		});
	});

	onMount(async () => {
		if (!browser) return;

		document.body.classList.add('wide');

		try {
			// Fetch personas and models in parallel
			const [personasRes, modelsRes] = await Promise.all([fetch(`${API_URL}/api/personas/dalston-clt`), fetch(`${API_URL}/api/models`)]);

			if (personasRes.ok) {
				const data = await personasRes.json();
				personas = data.personas || [];
			}

			if (modelsRes.ok) {
				const data = await modelsRes.json();
				models = data.models;
			}
		} catch (e) {
			error = 'Could not connect to API server. Make sure it is running.';
			console.error('API error:', e);
		} finally {
			loadingPersonas = false;
		}

		return () => {
			document.body.classList.remove('wide');
		};
	});

	async function estimateCost() {
		if (personas.length === 0) return;

		phase = 'estimate';

		try {
			const response = await fetch(`${API_URL}/api/survey/estimate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: {
						question_id: 'garden_use',
						question_text:
							'A 0.3-acre plot of land near your home in Dalston has been collectively purchased by your Community Land Trust. The 100 residents (including you) must decide what to do with it. Which of these options would you vote for?',
						options: gardenOptions,
						model: selectedModel
					},
					sample_persona: {
						id: personas[0].id,
						name: personas[0].name,
						context: personas[0].context
					},
					num_personas: personas.length
				})
			});

			if (response.ok) {
				costEstimate = await response.json();
			} else {
				throw new Error('Failed to get cost estimate');
			}
		} catch (e) {
			error = e.message;
			phase = 'intro';
		}
	}

	async function runSurvey() {
		phase = 'surveying';
		surveyProgress = 0;
		surveyResults = [];
		totalCost = 0;

		try {
			const response = await fetch(`${API_URL}/api/survey/run`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: {
						question_id: 'garden_use',
						question_text:
							'A 0.3-acre plot of land near your home in Dalston has been collectively purchased by your Community Land Trust. The 100 residents (including you) must decide what to do with it. Which of these options would you vote for?',
						options: gardenOptions,
						model: selectedModel
					},
					personas: personas.map((p) => ({
						id: p.id,
						name: p.name,
						context: p.context
					}))
				})
			});

			if (response.ok) {
				const data = await response.json();
				surveyResults = data.responses;
				totalCost = data.total_cost;
				phase = 'results';

				// Set the winning option
				if (voteTallies.length > 0) {
					winningOption = voteTallies[0][0];
				}
			} else {
				throw new Error('Survey failed');
			}
		} catch (e) {
			error = e.message;
			phase = 'intro';
		}
	}

	async function generateFollowUpQuestions() {
		if (!winningOption) return;

		// Generate 3 design questions focused on function and aesthetics (for image generation)
		const questions = [];

		if (winningOption.includes('vegetable') || winningOption.includes('garden') || winningOption.includes('allotment') || winningOption.includes('orchard') || winningOption.includes('herb') || winningOption.includes('farm')) {
			questions.push(
				{
					id: 'layout_style',
					text: 'What visual layout style should the growing space have?',
					options: [
						'Neat geometric raised beds with gravel paths',
						'Informal cottage garden style with winding paths',
						'Traditional allotment rows with wooden plot markers',
						'Modern urban farm with sleek planters and trellises',
						'Permaculture forest garden with layered planting'
					]
				},
				{
					id: 'key_features',
					text: 'What key visual features should be included?',
					options: [
						'A central greenhouse or polytunnel',
						'Fruit tree archways and espaliers',
						'A rustic wooden tool shed with green roof',
						'Colourful bean poles and climbing frames',
						'A communal seating area with pergola'
					]
				},
				{
					id: 'atmosphere',
					text: 'What atmosphere should the space convey?',
					options: [
						'Productive and abundant - overflowing with vegetables',
						'Peaceful and meditative - a green sanctuary',
						'Social and bustling - people working together',
						'Wild and naturalistic - blending with nature',
						'Educational and inspiring - demonstration gardens'
					]
				}
			);
		} else if (winningOption.includes('playground') || winningOption.includes('children') || winningOption.includes('adventure')) {
			questions.push(
				{
					id: 'design_theme',
					text: 'What design theme should the playground have?',
					options: [
						'Natural adventure - logs, boulders, rope bridges',
						'Colourful modern - bright equipment and rubber surfacing',
						'Imaginative themed - pirate ship or castle structure',
						'Minimalist Scandinavian - wood and muted colours',
						'Inclusive sensory - tactile elements and accessible equipment'
					]
				},
				{
					id: 'key_elements',
					text: 'What should be the central feature?',
					options: [
						'A large climbing structure with slides',
						'A natural water play area with pumps and channels',
						'A hill with tunnels and slides built into it',
						'A creative sand and mud kitchen area',
						'Musical instruments and sensory panels'
					]
				},
				{
					id: 'surrounding_design',
					text: 'What should surround the play area?',
					options: [
						'Shaded seating areas with native hedging',
						'A wildflower meadow with mown paths',
						'Picnic lawn with scattered trees',
						'Sensory planting beds children can explore',
						'A circular path for bikes and scooters'
					]
				}
			);
		} else if (winningOption.includes('wildflower') || winningOption.includes('wildlife') || winningOption.includes('pond') || winningOption.includes('meadow') || winningOption.includes('rewild') || winningOption.includes('sanctuary') || winningOption.includes('woodland')) {
			questions.push(
				{
					id: 'habitat_style',
					text: 'What should be the dominant habitat character?',
					options: [
						'Colourful wildflower meadow with grasses',
						'Native woodland copse with dappled shade',
						'Wetland with pond and marginal planting',
						'Mixed mosaic of meadow, scrub and trees',
						'Formal nature reserve with distinct zones'
					]
				},
				{
					id: 'human_elements',
					text: 'What human elements should be visible?',
					options: [
						'Rustic wooden benches and bird hides',
						'Winding mown grass paths only',
						'A small wooden boardwalk over wet areas',
						'Interpretation boards and bug hotels',
						'Almost nothing - let nature dominate'
					]
				},
				{
					id: 'seasonal_character',
					text: 'What season should the image capture?',
					options: [
						'Summer - full bloom with butterflies and bees',
						'Spring - emerging growth and nesting birds',
						'Autumn - seed heads and golden grasses',
						'Year-round interest - evergreen structure',
						'Dawn or dusk - magical golden light'
					]
				}
			);
		} else if (winningOption.includes('pavilion') || winningOption.includes('amphitheatre') || winningOption.includes('event') || winningOption.includes('cinema') || winningOption.includes('gathering')) {
			questions.push(
				{
					id: 'architecture_style',
					text: 'What architectural style should the structure have?',
					options: [
						'Contemporary timber with green roof',
						'Industrial reclaimed materials - steel and wood',
						'Traditional bandstand or gazebo style',
						'Minimalist concrete amphitheatre steps',
						'Tensile fabric canopy - light and temporary'
					]
				},
				{
					id: 'integration',
					text: 'How should the structure sit in the landscape?',
					options: [
						'Nestled into planted earth banks',
						'Open to a central lawn area',
						'Surrounded by ornamental grasses',
						'Under a canopy of mature trees',
						'Adjacent to a reflecting pool'
					]
				},
				{
					id: 'activity_shown',
					text: 'What activity should the image suggest?',
					options: [
						'Community gathering with string lights at dusk',
						'Outdoor cinema night with blankets',
						'Live music performance',
						'Quiet daytime reading and relaxation',
						'Children playing while adults chat'
					]
				}
			);
		} else if (winningOption.includes('sensory') || winningOption.includes('meditation') || winningOption.includes('therapeutic') || winningOption.includes('contemplation') || winningOption.includes('wellbeing') || winningOption.includes('forest bathing')) {
			questions.push(
				{
					id: 'design_approach',
					text: 'What design approach should the garden take?',
					options: [
						'Japanese-inspired with raked gravel and bamboo',
						'Sensory abundance - textures, scents, sounds',
						'Minimal and calming - green and white planting',
						'Enclosed garden rooms with hedges',
						'Naturalistic woodland glade'
					]
				},
				{
					id: 'water_element',
					text: 'What water feature should be included?',
					options: [
						'Still reflecting pool',
						'Gentle bubbling fountain',
						'Natural stream or rill',
						'Rain garden with seasonal water',
						'No water feature'
					]
				},
				{
					id: 'seating_style',
					text: 'What seating should be provided?',
					options: [
						'Curved wooden benches in secluded spots',
						'Meditation platforms and cushion areas',
						'Hammocks and swing seats',
						'Stone seats integrated into planting',
						'Accessible raised seating with backs'
					]
				}
			);
		} else {
			// Generic design questions for other options
			questions.push(
				{
					id: 'overall_aesthetic',
					text: 'What overall aesthetic should the space have?',
					options: [
						'Modern and clean - geometric lines and minimal planting',
						'Natural and organic - curves and native plants',
						'Colourful and playful - bold colours and varied textures',
						'Traditional English garden - formal beds and hedges',
						'Urban industrial - reclaimed materials and grasses'
					]
				},
				{
					id: 'focal_point',
					text: 'What should be the main focal point?',
					options: [
						'A striking central tree or sculpture',
						'A community gathering structure',
						'A water feature',
						'Naturalistic planting beds',
						'An open flexible lawn area'
					]
				},
				{
					id: 'boundary_treatment',
					text: 'How should the boundaries be treated?',
					options: [
						'Native hedgerow for wildlife',
						'Open and welcoming - no barriers',
						'Living willow screens',
						'Mixed shrub and perennial borders',
						'Low walls with integrated seating'
					]
				}
			);
		}

		followUpQuestions = questions;

		// Automatically proceed to cost estimate
		await estimateFollowUpCost();
	}

	async function estimateFollowUpCost() {
		if (personas.length === 0 || followUpQuestions.length === 0) return;

		phase = 'followup-estimate';

		try {
			// Estimate for all 5 questions
			const totalPromptTokens = 0;
			const totalCompletionTokens = 0;
			let costPerAgent = 0;

			// Use first question as sample - multiply by 5
			const response = await fetch(`${API_URL}/api/survey/estimate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: {
						question_id: followUpQuestions[0].id,
						question_text: followUpQuestions[0].text,
						options: followUpQuestions[0].options,
						model: selectedModel
					},
					sample_persona: {
						id: personas[0].id,
						name: personas[0].name,
						context: personas[0].context
					},
					num_personas: personas.length
				})
			});

			if (response.ok) {
				const estimate = await response.json();
				followUpCostEstimate = {
					...estimate,
					prompt_tokens: estimate.prompt_tokens * 3,
					completion_tokens: estimate.completion_tokens * 3,
					cost_per_agent: estimate.cost_per_agent * 3,
					total_cost: estimate.total_cost * 3,
					num_questions: 3
				};
			} else {
				throw new Error('Failed to get cost estimate');
			}
		} catch (e) {
			error = e.message;
			phase = 'results';
		}
	}

	async function runFollowUpSurvey() {
		phase = 'followup-surveying';
		followUpResults = [];
		currentFollowUpQuestion = 0;

		try {
			for (let i = 0; i < followUpQuestions.length; i++) {
				currentFollowUpQuestion = i + 1;
				const q = followUpQuestions[i];

				const response = await fetch(`${API_URL}/api/survey/run`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						question: {
							question_id: q.id,
							question_text: q.text,
							options: q.options,
							model: selectedModel
						},
						personas: personas.map((p) => ({
							id: p.id,
							name: p.name,
							context: p.context
						}))
					})
				});

				if (response.ok) {
					const data = await response.json();
					const resultsWithIndex = data.responses.map((r) => ({ ...r, question_index: i }));
					followUpResults = [...followUpResults, ...resultsWithIndex];
					totalCost += data.total_cost;
				}
			}

			phase = 'followup-results';
		} catch (e) {
			error = e.message;
			phase = 'results';
		}
	}

	function reset() {
		phase = 'intro';
		surveyResults = [];
		followUpResults = [];
		followUpQuestions = [];
		costEstimate = null;
		followUpCostEstimate = null;
		totalCost = 0;
		winningOption = null;
		generatedImage = null;
		imagePrompt = null;
		imageError = null;
	}

	async function generateGardenImage() {
		if (!winningOption || followUpTallies.length === 0) return;

		generatingImage = true;
		imageError = null;

		// Build design choices from the winning answers
		const designChoices = followUpTallies.map((tally, i) => ({
			question: followUpQuestions[i].text,
			answer: tally.tallies[0]?.[0] || 'Not specified'
		}));

		try {
			const response = await fetch(`${API_URL}/api/generate-garden-image`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					winning_option: winningOption,
					design_choices: designChoices
				})
			});

			const data = await response.json();

			if (data.error) {
				throw new Error(data.error);
			}

			generatedImage = data.image_base64;
			imagePrompt = data.prompt_used;
		} catch (e) {
			imageError = e.message;
		} finally {
			generatingImage = false;
		}
	}

	function formatCost(cost) {
		return `$${cost.toFixed(4)}`;
	}

	function formatPercent(count, total) {
		return `${((count / total) * 100).toFixed(1)}%`;
	}

	function getAgeGroups(voters) {
		return voters.reduce(
			(acc, v) => {
				if (!v.persona) return acc;
				const age = v.persona.age;
				if (age < 30) acc['Under 30']++;
				else if (age < 50) acc['30-49']++;
				else if (age < 65) acc['50-64']++;
				else acc['65+']++;
				return acc;
			},
			{ 'Under 30': 0, '30-49': 0, '50-64': 0, '65+': 0 }
		);
	}

	function getOccupations(voters) {
		const occupations = voters.reduce((acc, v) => {
			if (!v.persona) return acc;
			const occ = v.persona.occupation || 'Unknown';
			acc[occ] = (acc[occ] || 0) + 1;
			return acc;
		}, {});
		return Object.entries(occupations).sort((a, b) => b[1] - a[1]);
	}
</script>

<svelte:head>
	<title>02: Dream a Garden</title>
</svelte:head>

<nav class="nav">
	<a href="/">&larr; Back to experiments</a>
</nav>

<header class="header">
	<h1>Dream a Garden</h1>
	<p class="subtitle">Experiment 02</p>
</header>

<div class="intro">
	<p>
		In early 2024, a peculiar opportunity emerged in Dalston, East London. A long-neglected 0.3-acre plot wedged between Victorian terraces
		<a href="https://www.standard.co.uk/homesandproperty/buying-mortgages/grand-designs-london-land-for-sale-planning-permission-developer-b1149255.html" target="_blank" rel="noopener"
			>came up for auction</a
		>
		after decades of legal limbo. Rather than watch it fall to yet another developer, forty-two neighbouring households—representing around 100 residents—formed an ad-hoc Community Land Trust and collectively
		acquired the site through a sealed-bid consortium structure.
	</p>

	<figure class="plot-image">
		<img src="/images/plot_1.png" alt="The plot of land in Dalston" />
		<figcaption>The site at the time of acquisition, March 2024</figcaption>
	</figure>

	<figure class="plot-image">
		<img src="/images/trust.png" alt="Satellite view showing the CLT member properties in blue surrounding the plot in green" />
		<figcaption>The forty-two CLT member properties (blue) surrounding the plot (green)</figcaption>
	</figure>

	<p>
		The CLT's operating agreement stipulates democratic governance via weighted quadratic voting—each household holds equal base voting power, with additional weight proportional to their proximity to
		the site. An asset lock prevents future sale for private gain. Whatever gets built here, stays community-owned in perpetuity.
	</p>

	<p>
		But what <em>should</em> be built? A community garden? Urban allotments? A pocket park with playground equipment? A rewilded biodiversity corridor? The hundred-odd residents represent a spectrum of
		needs: young families, retired couples, remote workers craving green space, long-time residents sceptical of change.
	</p>

	<p>
		This experiment asks: can we simulate the deliberation? We've generated synthetic personas representing each household, informed by demographic patterns of the E8 postcode. Now we'll survey them
		on proposals for the land—tracking how different framings, trade-offs, and community dynamics shape the outcome.
	</p>

	<h2>The Question</h2>

	<p>If silicon can dream, what garden would it grow?</p>
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

{#if loadingPersonas}
	<div class="status-box">
		<p>Loading personas...</p>
	</div>
{:else if personas.length === 0}
	<div class="status-box">
		<p><strong>No personas found.</strong> Run notebook 03 first to generate the Dalston CLT personas.</p>
	</div>
{:else if phase === 'intro'}
	<div class="survey-section">
		<h2>The Survey</h2>
		<p>We have <strong>{personas.length} synthetic residents</strong> ready to vote on what should be done with the plot.</p>

		<div class="options-preview">
			<h3>The 30 Options</h3>
			<div class="options-grid">
				{#each gardenOptions as option, i}
					<div class="option-item">
						<span class="option-number">{i + 1}.</span>
						{option}
					</div>
				{/each}
			</div>
		</div>

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

		<button onclick={estimateCost}>Get Cost Estimate</button>
	</div>
{:else if phase === 'estimate'}
	<div class="survey-section">
		<h2>Cost Estimate</h2>

		{#if costEstimate}
			<div class="estimate-card">
				<h3>Survey: {costEstimate.num_agents} personas x 1 question (30 options)</h3>
				<dl class="estimate-details">
					<dt>Prompt tokens per agent</dt>
					<dd>{costEstimate.prompt_tokens.toLocaleString()}</dd>

					<dt>Completion tokens per agent</dt>
					<dd>{costEstimate.completion_tokens.toLocaleString()}</dd>

					<dt>Cost per agent</dt>
					<dd>{formatCost(costEstimate.cost_per_agent)}</dd>

					<dt>Total estimated cost</dt>
					<dd class="total-cost">{formatCost(costEstimate.total_cost)}</dd>
				</dl>
			</div>

			<div class="action-buttons">
				<button onclick={runSurvey} class="primary">Run Survey</button>
				<button onclick={() => (phase = 'intro')} class="secondary">Cancel</button>
			</div>
		{:else}
			<p>Calculating estimate...</p>
		{/if}
	</div>
{:else if phase === 'surveying'}
	<div class="survey-section">
		<h2>Survey in Progress</h2>
		<p>Surveying {personas.length} personas on their garden preferences...</p>
		<div class="progress-bar">
			<div class="progress-fill" style="width: 100%"></div>
		</div>
		<p class="progress-text">Processing all {personas.length} responses concurrently...</p>
	</div>
{:else if phase === 'results'}
	<div class="results-section">
		<h2>Survey Results</h2>

		<div class="results-summary">
			<p><strong>{surveyResults.length}</strong> votes collected | Total cost: <strong>{formatCost(totalCost)}</strong></p>
		</div>

		{#if voteTallies.length > 0}
			<div class="winner-announcement">
				<h3>The Winner</h3>
				<p class="winner-text">{voteTallies[0][0]}</p>
				<p class="winner-votes">{voteTallies[0][1]} votes ({formatPercent(voteTallies[0][1], surveyResults.length)})</p>
			</div>

			<div class="tallies-section">
				<h3>Full Results</h3>
				<div class="bar-chart">
					{#each voteTallies as [option, count]}
						<div class="bar-row">
							<span class="bar-label" title={option}>{option.length > 45 ? option.slice(0, 45) + '...' : option}</span>
							<div class="bar-track">
								<div class="bar bar-vote" style="width: {Math.max((count / surveyResults.length) * 100, count > 0 ? 2 : 0)}%"></div>
							</div>
							<span class="bar-value">{count} <span class="bar-percent">({formatPercent(count, surveyResults.length)})</span></span>
						</div>
					{/each}
				</div>
			</div>

			<div class="demographics-section">
				<h3>Who Voted for the Winner?</h3>
				<p>Let's look at who chose "{voteTallies[0][0]}":</p>

				{#if topChoiceVoters.length > 0}
					<div class="voter-breakdown">
						<div class="breakdown-stat">
							<h4>Age Groups</h4>
							{#each Object.entries(getAgeGroups(topChoiceVoters)).filter(([_, c]) => c > 0) as [group, count]}
								<p>{group}: {count} ({formatPercent(count, topChoiceVoters.length)})</p>
							{/each}
						</div>

						<div class="breakdown-stat">
							<h4>Occupations</h4>
							{#each getOccupations(topChoiceVoters).slice(0, 5) as [occ, count]}
								<p>{occ}: {count}</p>
							{/each}
						</div>

						<div class="breakdown-stat">
							<h4>Sample Voters</h4>
							{#each topChoiceVoters.slice(0, 5) as voter}
								<p>{voter.persona?.name || voter.persona_name} ({voter.persona?.age || '?'}, {voter.persona?.occupation || '?'})</p>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<div class="individual-responses">
				<h3>All Individual Responses</h3>
				<details>
					<summary>Show all {surveyResults.length} responses</summary>
					<div class="responses-list">
						{#each surveyResults as response}
							{@const persona = personas.find((p) => p.id === response.persona_id)}
							<div class="response-item">
								<span class="response-name">{response.persona_name}</span>
								<span class="response-meta">{persona?.age || '?'}, {persona?.occupation || '?'}</span>
								<span class="response-vote">{response.response}</span>
							</div>
						{/each}
					</div>
				</details>
			</div>

			<div class="followup-section">
				<h2>Phase 2: Design Decisions</h2>
				<p>The community has chosen <strong>"{winningOption}"</strong>. Now we need to make 5 key design decisions about how to implement it.</p>
				<button onclick={generateFollowUpQuestions}>Generate Follow-up Questions</button>
			</div>
		{/if}
	</div>
{:else if phase === 'followup-estimate' && followUpQuestions.length > 0}
	<div class="survey-section">
		<h2>Follow-up Survey Cost Estimate</h2>

		<div class="followup-questions-preview">
			<h3>3 Design Questions (for image generation)</h3>
			{#each followUpQuestions as q, i}
				<div class="question-preview">
					<h4>Q{i + 1}: {q.text}</h4>
					<ul>
						{#each q.options as opt}
							<li>{opt}</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>

		{#if followUpCostEstimate}
			<div class="estimate-card">
				<h3>Survey: {followUpCostEstimate.num_agents} personas x {followUpCostEstimate.num_questions} questions</h3>
				<dl class="estimate-details">
					<dt>Total prompt tokens</dt>
					<dd>{followUpCostEstimate.prompt_tokens.toLocaleString()}</dd>

					<dt>Total completion tokens</dt>
					<dd>{followUpCostEstimate.completion_tokens.toLocaleString()}</dd>

					<dt>Total estimated cost</dt>
					<dd class="total-cost">{formatCost(followUpCostEstimate.total_cost)}</dd>
				</dl>
			</div>

			<div class="action-buttons">
				<button onclick={runFollowUpSurvey} class="primary">Run Follow-up Survey</button>
				<button onclick={() => (phase = 'results')} class="secondary">Back to Results</button>
			</div>
		{:else}
			<p>Calculating estimate...</p>
		{/if}
	</div>
{:else if phase === 'followup-surveying'}
	<div class="survey-section">
		<h2>Follow-up Survey in Progress</h2>
		<p>
			Question {currentFollowUpQuestion} of {followUpQuestions.length}: {followUpQuestions[currentFollowUpQuestion - 1]?.text || ''}
		</p>
		<div class="progress-bar">
			<div class="progress-fill" style="width: {(currentFollowUpQuestion / followUpQuestions.length) * 100}%"></div>
		</div>
		<p class="progress-text">{followUpResults.length} responses collected so far...</p>
	</div>
{:else if phase === 'followup-results'}
	<div class="results-section">
		<h2>Follow-up Survey Results</h2>

		<div class="results-summary">
			<p>
				<strong>{followUpResults.length}</strong> total responses across {followUpQuestions.length} questions | Total cost so far: <strong>{formatCost(totalCost)}</strong>
			</p>
		</div>

		{#each followUpTallies as tally, i}
			<div class="followup-result">
				<h3>Q{i + 1}: {tally.question}</h3>
				<div class="bar-chart">
					{#each tally.tallies as [option, count]}
						<div class="bar-row">
							<span class="bar-label" title={option}>{option.length > 50 ? option.slice(0, 50) + '...' : option}</span>
							<div class="bar-track">
								<div class="bar bar-followup" style="width: {Math.max((count / personas.length) * 100, count > 0 ? 2 : 0)}%"></div>
							</div>
							<span class="bar-value">{count} <span class="bar-percent">({formatPercent(count, personas.length)})</span></span>
						</div>
					{/each}
				</div>
			</div>
		{/each}

		<div class="final-summary">
			<h2>The Community's Vision</h2>
			<p>Based on the survey of {personas.length} synthetic Dalston residents:</p>
			<ul class="vision-list">
				<li><strong>Main Use:</strong> {winningOption}</li>
				{#each followUpTallies as tally, i}
					{@const winner = tally.tallies[0]}
					{#if winner}
						<li><strong>{followUpQuestions[i].text.split('?')[0]}:</strong> {winner[0]}</li>
					{/if}
				{/each}
			</ul>
		</div>

		<div class="image-generation-section">
			<h2>Generate the Vision</h2>
			<p>Transform the empty plot into the community's chosen design using AI image generation.</p>

			{#if imageError}
				<div class="error-box">
					<p class="error">{imageError}</p>
				</div>
			{/if}

			{#if !generatedImage && !generatingImage}
				<div class="before-after-preview">
					<div class="preview-image">
						<h4>Current Plot</h4>
						<img src="/images/plot_1.png" alt="The empty plot" />
					</div>
					<div class="arrow">→</div>
					<div class="preview-image placeholder-image">
						<h4>Community Vision</h4>
						<div class="placeholder">Click below to generate</div>
					</div>
				</div>
				<button onclick={generateGardenImage} class="primary generate-btn">
					Generate Garden Image
				</button>
			{:else if generatingImage}
				<div class="generating-status">
					<div class="spinner"></div>
					<p>Generating your community garden vision...</p>
					<p class="generating-hint">This may take 30-60 seconds</p>
				</div>
			{:else if generatedImage}
				<div class="before-after">
					<div class="before-after-images">
						<div class="ba-image">
							<h4>Before</h4>
							<img src="/images/plot_1.png" alt="The empty plot" />
						</div>
						<div class="ba-image">
							<h4>After: The Community's Choice</h4>
							<img src="data:image/png;base64,{generatedImage}" alt="Generated garden design" />
						</div>
					</div>
				</div>

				<details class="prompt-details">
					<summary>View generation prompt</summary>
					<pre class="prompt-text">{imagePrompt}</pre>
				</details>

				<div class="action-buttons">
					<button onclick={generateGardenImage} class="secondary">Regenerate Image</button>
				</div>
			{/if}
		</div>

		<div class="action-buttons final-actions">
			<button onclick={reset} class="secondary">Start Over</button>
		</div>
	</div>
{/if}

<style>
	.header {
		margin-bottom: 0.5rem;
	}

	.intro {
		margin-bottom: 2rem;
	}

	.intro p {
		line-height: 1.7;
	}

	.intro h2 {
		margin-top: 2rem;
		margin-bottom: 0.75rem;
		font-size: 1.3rem;
	}

	.plot-image {
		margin: 2rem 0;
		padding: 0;
	}

	.plot-image img {
		width: 100%;
		max-width: 700px;
		border: 1px solid #ddd;
		border-radius: 4px;
	}

	.plot-image figcaption {
		margin-top: 0.5rem;
		font-size: 0.9rem;
		color: #666;
		font-style: italic;
	}

	.status-box,
	.error-box {
		background: #f5f5f5;
		border-left: 3px solid var(--accent);
		padding: 1rem 1.5rem;
		margin-top: 2rem;
	}

	.error-box {
		background: #fff5f5;
		border-color: #c00;
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

	.survey-section,
	.results-section {
		margin-top: 2rem;
		padding-top: 2rem;
		border-top: 2px solid var(--border);
	}

	.survey-section h2,
	.results-section h2 {
		margin-top: 0;
		color: var(--accent);
	}

	.options-preview {
		margin: 2rem 0;
		background: #fafafa;
		padding: 1.5rem;
		border-radius: 4px;
	}

	.options-preview h3 {
		margin-top: 0;
		margin-bottom: 1rem;
		font-size: 1.1rem;
	}

	.options-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 0.5rem;
	}

	.option-item {
		font-size: 0.9rem;
		padding: 0.4rem 0;
	}

	.option-number {
		color: #999;
		font-family: monospace;
		margin-right: 0.5rem;
	}

	.model-selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin: 1.5rem 0;
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
	}

	.estimate-card {
		background: #f9f9f9;
		border-left: 3px solid var(--accent);
		padding: 1.5rem;
		margin: 1.5rem 0;
	}

	.estimate-card h3 {
		margin-top: 0;
		margin-bottom: 1rem;
		font-size: 1.1rem;
	}

	.estimate-details {
		display: grid;
		grid-template-columns: auto auto;
		gap: 0.5rem 2rem;
	}

	.estimate-details dt {
		color: #666;
	}

	.estimate-details dd {
		margin: 0;
		font-weight: 500;
	}

	.total-cost {
		color: var(--accent);
		font-size: 1.2rem;
	}

	.action-buttons {
		display: flex;
		gap: 1rem;
		margin-top: 1.5rem;
	}

	.action-buttons button {
		margin-top: 0;
	}

	.primary {
		background: var(--accent);
	}

	.secondary {
		background: #666;
	}

	.progress-bar {
		width: 100%;
		height: 24px;
		background: #e0e0e0;
		border-radius: 4px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent);
		transition: width 0.3s ease;
	}

	.progress-text {
		text-align: center;
		color: #666;
		font-size: 0.9rem;
	}

	.results-summary {
		background: #f0f8f0;
		padding: 1rem 1.5rem;
		border-radius: 4px;
		margin-bottom: 2rem;
	}

	.results-summary p {
		margin: 0;
	}

	.winner-announcement {
		text-align: center;
		padding: 2rem;
		background: linear-gradient(135deg, #f5f0e6, #fff);
		border: 2px solid var(--accent);
		border-radius: 8px;
		margin-bottom: 2rem;
	}

	.winner-announcement h3 {
		margin-top: 0;
		color: #666;
		font-size: 1rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.winner-text {
		font-size: 1.5rem;
		font-weight: 500;
		color: var(--accent);
		margin-bottom: 0.5rem;
	}

	.winner-votes {
		color: #666;
		font-size: 1.1rem;
		margin-bottom: 0;
	}

	.tallies-section,
	.demographics-section,
	.individual-responses,
	.followup-section {
		margin-top: 2rem;
	}

	.tallies-section h3,
	.demographics-section h3,
	.individual-responses h3,
	.followup-section h2 {
		margin-bottom: 1rem;
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
		width: 300px;
		flex-shrink: 0;
		font-size: 0.85rem;
		color: #555;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.bar-track {
		flex: 1;
		height: 20px;
		background: #e8e8e8;
		border-radius: 3px;
		overflow: hidden;
	}

	.bar {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}

	.bar-vote {
		background: var(--accent);
	}

	.bar-followup {
		background: #2e7d32;
	}

	.bar-value {
		width: 80px;
		flex-shrink: 0;
		font-size: 0.85rem;
		color: #555;
		text-align: right;
	}

	.bar-percent {
		color: #888;
	}

	.voter-breakdown {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1.5rem;
		margin-top: 1rem;
	}

	.breakdown-stat {
		background: #fafafa;
		padding: 1rem;
		border-radius: 4px;
	}

	.breakdown-stat h4 {
		margin-top: 0;
		margin-bottom: 0.75rem;
		font-size: 0.95rem;
		color: #666;
	}

	.breakdown-stat p {
		margin-bottom: 0.25rem;
		font-size: 0.9rem;
	}

	.responses-list {
		max-height: 400px;
		overflow-y: auto;
		margin-top: 1rem;
	}

	.response-item {
		display: grid;
		grid-template-columns: 150px 180px 1fr;
		gap: 1rem;
		padding: 0.5rem 0;
		border-bottom: 1px solid #eee;
		font-size: 0.9rem;
	}

	.response-name {
		font-weight: 500;
	}

	.response-meta {
		color: #666;
	}

	.response-vote {
		color: var(--accent);
	}

	details summary {
		cursor: pointer;
		color: var(--accent);
		font-weight: 500;
	}

	.followup-section {
		padding-top: 2rem;
		border-top: 2px solid #ddd;
	}

	.followup-questions-preview {
		margin: 1.5rem 0;
	}

	.question-preview {
		background: #fafafa;
		padding: 1rem 1.5rem;
		border-radius: 4px;
		margin-bottom: 1rem;
	}

	.question-preview h4 {
		margin-top: 0;
		margin-bottom: 0.75rem;
		color: var(--accent);
	}

	.question-preview ul {
		margin: 0;
		padding-left: 1.5rem;
	}

	.question-preview li {
		font-size: 0.9rem;
		margin-bottom: 0.25rem;
	}

	.followup-result {
		margin-bottom: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.followup-result h3 {
		color: var(--accent);
		font-size: 1.1rem;
		margin-bottom: 1rem;
	}

	.final-summary {
		background: linear-gradient(135deg, #f5f0e6, #fff);
		border: 2px solid var(--accent);
		border-radius: 8px;
		padding: 2rem;
		margin-top: 2rem;
	}

	.final-summary h2 {
		margin-top: 0;
		color: var(--accent);
	}

	.vision-list {
		list-style: none;
		padding: 0;
	}

	.vision-list li {
		padding: 0.5rem 0;
		border-bottom: 1px solid #eee;
	}

	.vision-list li:last-child {
		border-bottom: none;
	}

	/* Image Generation Styles */
	.image-generation-section {
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 2px solid var(--accent);
	}

	.image-generation-section h2 {
		color: var(--accent);
		margin-top: 0;
	}

	.before-after-preview,
	.before-after-images {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 1.5rem;
		align-items: center;
		margin: 2rem 0;
	}

	.preview-image,
	.ba-image {
		text-align: center;
	}

	.preview-image img,
	.ba-image img {
		width: 100%;
		max-width: 400px;
		border: 1px solid #ddd;
		border-radius: 4px;
	}

	.preview-image h4,
	.ba-image h4 {
		margin-bottom: 0.75rem;
		color: #666;
		font-size: 1rem;
	}

	.arrow {
		font-size: 2rem;
		color: var(--accent);
	}

	.placeholder-image .placeholder {
		width: 100%;
		max-width: 400px;
		height: 300px;
		background: #f5f5f5;
		border: 2px dashed #ccc;
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #999;
		font-style: italic;
		margin: 0 auto;
	}

	.generate-btn {
		display: block;
		margin: 0 auto;
		font-size: 1.1rem;
		padding: 0.8rem 2rem;
	}

	.generating-status {
		text-align: center;
		padding: 3rem;
	}

	.spinner {
		width: 48px;
		height: 48px;
		border: 4px solid #e0e0e0;
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 1.5rem;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.generating-hint {
		color: #888;
		font-size: 0.9rem;
	}

	.before-after {
		margin: 2rem 0;
	}

	.prompt-details {
		margin-top: 1.5rem;
		background: #f9f9f9;
		border-radius: 4px;
		padding: 1rem;
	}

	.prompt-details summary {
		cursor: pointer;
		color: var(--accent);
		font-weight: 500;
	}

	.prompt-text {
		margin-top: 1rem;
		white-space: pre-wrap;
		font-size: 0.85rem;
		line-height: 1.5;
		color: #555;
	}

	.final-actions {
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 1px solid #ddd;
	}

	@media (max-width: 768px) {
		.options-grid {
			grid-template-columns: 1fr;
		}

		.bar-label {
			width: 150px;
		}

		.response-item {
			grid-template-columns: 1fr;
			gap: 0.25rem;
		}

		.voter-breakdown {
			grid-template-columns: 1fr;
		}

		.before-after-preview,
		.before-after-images {
			grid-template-columns: 1fr;
			gap: 1rem;
		}

		.arrow {
			transform: rotate(90deg);
		}
	}
</style>
