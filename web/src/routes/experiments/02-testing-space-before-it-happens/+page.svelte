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

	// Household visualization state
	let households = $state([]);
	let selectedHousehold = $state(null);
	let selectedPerson = $state(null);
	let personFiles = $state([]);
	let loadingFiles = $state(false);

	// Group households by street for map layout
	let streetGroups = $derived.by(() => {
		const groups = {};
		households.forEach(h => {
			const street = h.address.street;
			if (!groups[street]) groups[street] = [];
			groups[street].push(h);
		});
		// Sort houses by number within each street
		Object.keys(groups).forEach(street => {
			groups[street].sort((a, b) => {
				const numA = parseInt(a.address.number.replace(/\D/g, '')) || 0;
				const numB = parseInt(b.address.number.replace(/\D/g, '')) || 0;
				return numA - numB;
			});
		});
		return groups;
	});

	function selectHousehold(household) {
		selectedHousehold = household;
		selectedPerson = null;
		personFiles = [];
	}

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

	// Sample data mode
	let useSampleData = $state(false);
	let sampleData = $state(null);
	let loadingSampleData = $state(false);

	// Track which model was used for the survey
	let surveyModelUsed = $state(null);

	// Track previous model to detect changes
	let previousModel = $state('gpt-4o-mini');

	// Recalculate follow-up cost when model changes during estimate phase
	$effect(() => {
		if (phase === 'followup-estimate' && selectedModel !== previousModel && followUpQuestions.length > 0) {
			previousModel = selectedModel;
			recalculateFollowUpCost();
		}
	});

	// Options for the plot (0.3 acres)
	const plotOptions = [
		'Allotments',
		'Playground',
		'Outdoor gym',
		'Pond',
		'Urban forest',
		'Sculpture park',
		'Junkyard',
		'Courtyard',
		'Carpark',
		'Urban caving entrance',
		'Portacabins'
	];

	// Computed: vote tallies
	let voteTallies = $derived.by(() => {
		if (surveyResults.length === 0) return [];

		const counts = {};
		plotOptions.forEach((opt) => (counts[opt] = 0));

		surveyResults.forEach((r) => {
			// Find the best matching option
			const response = r.response.toLowerCase().trim();
			let matched = false;

			for (const opt of plotOptions) {
				if (response.includes(opt.toLowerCase()) || opt.toLowerCase().includes(response)) {
					counts[opt]++;
					matched = true;
					break;
				}
			}

			// Fuzzy matching - check if any option words are in the response
			if (!matched) {
				for (const opt of plotOptions) {
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
			// Fetch personas, households, and models in parallel
			const [personasRes, householdsRes, modelsRes] = await Promise.all([
				fetch(`${API_URL}/api/personas/dalston-clt`),
				fetch(`${API_URL}/api/households/dalston-clt`),
				fetch(`${API_URL}/api/models`)
			]);

			if (personasRes.ok) {
				const data = await personasRes.json();
				personas = data.personas || [];
			}

			if (householdsRes.ok) {
				const data = await householdsRes.json();
				households = data.households || [];
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

	async function selectPerson(person, household) {
		selectedPerson = { ...person, household };
		loadingFiles = true;
		personFiles = [];

		try {
			const res = await fetch(`${API_URL}/api/persona-files/${person.id}`);
			if (res.ok) {
				const data = await res.json();
				personFiles = data.files || [];
			}
		} catch (e) {
			console.error('Failed to load persona files:', e);
		} finally {
			loadingFiles = false;
		}
	}

	function closePerson() {
		selectedPerson = null;
		personFiles = [];
	}

	function closeHousehold() {
		selectedHousehold = null;
		selectedPerson = null;
		personFiles = [];
	}

	async function estimateCost() {
		if (personas.length === 0) return;

		phase = 'estimate';

		try {
			const response = await fetch(`${API_URL}/api/survey/estimate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: {
						question_id: 'plot_use',
						question_text:
							'A 0.3-acre plot of land near your home in Dalston has been collectively purchased by your Community Land Trust. The 100 residents (including you) must decide what to do with it. Which of these options would you vote for?',
						options: plotOptions,
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
		surveyModelUsed = selectedModel;

		try {
			const response = await fetch(`${API_URL}/api/survey/run`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: {
						question_id: 'plot_use',
						question_text:
							'A 0.3-acre plot of land near your home in Dalston has been collectively purchased by your Community Land Trust. The 100 residents (including you) must decide what to do with it. Which of these options would you vote for?',
						options: plotOptions,
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

		// Generate 3 simple, concrete design questions
		const questions = [];
		const option = winningOption.toLowerCase();

		if (option.includes('allotment')) {
			questions.push(
				{
					id: 'plot_style',
					text: 'How should the plots be laid out?',
					options: ['Raised beds', 'Ground-level rows', 'Mixed sizes for different needs']
				},
				{
					id: 'shared_facility',
					text: 'What shared facility is most important?',
					options: ['Tool shed', 'Greenhouse', 'Composting area', 'Water taps throughout']
				},
				{
					id: 'paths',
					text: 'What should the paths be made of?',
					options: ['Gravel', 'Wood chip', 'Paved slabs', 'Mown grass']
				}
			);
		} else if (option.includes('playground')) {
			questions.push(
				{
					id: 'age_group',
					text: 'What age group should it focus on?',
					options: ['Toddlers (under 5)', 'Children (5-12)', 'All ages mixed']
				},
				{
					id: 'main_equipment',
					text: 'What should be the main equipment?',
					options: ['Climbing frame with slide', 'Swings', 'Natural play (logs, boulders)', 'Water play']
				},
				{
					id: 'surface',
					text: 'What should the ground surface be?',
					options: ['Rubber safety surface', 'Wood chip', 'Sand', 'Grass']
				}
			);
		} else if (option.includes('gym')) {
			questions.push(
				{
					id: 'equipment_type',
					text: 'What type of equipment?',
					options: ['Bodyweight stations', 'Cardio machines', 'Calisthenics bars', 'Mixed variety']
				},
				{
					id: 'surface',
					text: 'What should the ground surface be?',
					options: ['Rubber matting', 'Artificial grass', 'Paved area', 'Natural grass']
				},
				{
					id: 'extras',
					text: 'What extra feature would be most useful?',
					options: ['Drinking fountain', 'Covered shelter', 'Stretching area', 'Running track around edge']
				}
			);
		} else if (option.includes('pond')) {
			questions.push(
				{
					id: 'pond_size',
					text: 'How large should the pond be?',
					options: ['Small wildlife pond', 'Medium pond with seating', 'Large pond with island']
				},
				{
					id: 'access',
					text: 'How should people access the pond?',
					options: ['Viewing platform', 'Boardwalk around edge', 'Natural banks to sit on', 'Dipping platform']
				},
				{
					id: 'surrounding',
					text: 'What should surround the pond?',
					options: ['Wetland plants', 'Wildflower meadow', 'Trees and shrubs', 'Lawn area']
				}
			);
		} else if (option.includes('urban forest') || option.includes('forest')) {
			questions.push(
				{
					id: 'tree_types',
					text: 'What type of trees?',
					options: ['Native woodland mix', 'Fruit and nut trees', 'Fast-growing for quick shade', 'Evergreen year-round']
				},
				{
					id: 'density',
					text: 'How dense should it be?',
					options: ['Dense woodland feel', 'Open with scattered trees', 'Mix of clearings and thickets']
				},
				{
					id: 'paths',
					text: 'What paths through the forest?',
					options: ['Winding woodland trails', 'Single loop path', 'Boardwalk', 'No formal paths']
				}
			);
		} else if (option.includes('sculpture') || option.includes('park')) {
			questions.push(
				{
					id: 'art_style',
					text: 'What style of sculptures?',
					options: ['Abstract modern', 'Figurative and traditional', 'Interactive installations', 'Local artist commissions']
				},
				{
					id: 'layout',
					text: 'How should it be laid out?',
					options: ['Formal paths between pieces', 'Scattered through gardens', 'Central plaza with surrounding pieces']
				},
				{
					id: 'landscape',
					text: 'What should the landscaping be?',
					options: ['Manicured lawns', 'Wildflower meadows', 'Gravel and paving', 'Mixed planting beds']
				}
			);
		} else if (option.includes('junkyard')) {
			questions.push(
				{
					id: 'purpose',
					text: 'What should the junkyard be for?',
					options: ['Adventure playground from scrap', 'Art installations from waste', 'Community repair workshop', 'Salvage and reuse depot']
				},
				{
					id: 'aesthetic',
					text: 'What aesthetic?',
					options: ['Organised chaos', 'Curated industrial', 'Hidden treasures', 'Colourful and artistic']
				},
				{
					id: 'access',
					text: 'Who should access it?',
					options: ['Open to all', 'Supervised sessions only', 'Members with training', 'Children with adults']
				}
			);
		} else if (option.includes('courtyard')) {
			questions.push(
				{
					id: 'style',
					text: 'What style of courtyard?',
					options: ['Mediterranean with tiles', 'Japanese zen garden', 'English cottage garden', 'Modern minimalist']
				},
				{
					id: 'centre',
					text: 'What should be in the centre?',
					options: ['Fountain or water feature', 'Large tree', 'Seating area', 'Open paved space']
				},
				{
					id: 'planting',
					text: 'What planting around the edges?',
					options: ['Climbing plants on walls', 'Potted plants', 'Formal hedges', 'Flowering borders']
				}
			);
		} else if (option.includes('carpark') || option.includes('car park')) {
			questions.push(
				{
					id: 'surface',
					text: 'What surface?',
					options: ['Tarmac', 'Gravel', 'Permeable paving', 'Grass reinforcement grid']
				},
				{
					id: 'capacity',
					text: 'How many spaces?',
					options: ['Maximum capacity', 'Half spaces, half green', 'Just a few spaces', 'Mainly bike parking']
				},
				{
					id: 'features',
					text: 'What additional features?',
					options: ['EV charging points', 'Trees for shade', 'Bike storage', 'None - just parking']
				}
			);
		} else if (option.includes('caving') || option.includes('cave')) {
			questions.push(
				{
					id: 'entrance_style',
					text: 'What style of entrance?',
					options: ['Natural rock formation', 'Built stone archway', 'Hidden and subtle', 'Dramatic and visible']
				},
				{
					id: 'above_ground',
					text: 'What should be above ground?',
					options: ['Equipment storage hut', 'Information centre', 'Just the entrance', 'Café and facilities']
				},
				{
					id: 'access',
					text: 'Who should access it?',
					options: ['Trained cavers only', 'Guided tours for public', 'Members with equipment', 'Open supervised sessions']
				}
			);
		} else if (option.includes('portacabin') || option.includes('porta')) {
			questions.push(
				{
					id: 'purpose',
					text: 'What should the portacabins be used for?',
					options: ['Community meeting rooms', 'Workspace and offices', 'Youth club', 'Storage and workshops']
				},
				{
					id: 'quantity',
					text: 'How many portacabins?',
					options: ['One large unit', 'Several small units', 'Clustered complex', 'Stacked two-storey']
				},
				{
					id: 'outside',
					text: 'What should surround them?',
					options: ['Paved area with seating', 'Garden and planting', 'Parking spaces', 'Fenced compound']
				}
			);
		} else {
			// Generic questions for any option
			questions.push(
				{
					id: 'style',
					text: 'What style should the space have?',
					options: ['Natural and informal', 'Neat and structured', 'Colourful and playful', 'Simple and low-maintenance']
				},
				{
					id: 'seating',
					text: 'What seating should be included?',
					options: ['Wooden benches', 'Picnic tables', 'Stone seats', 'Flexible (bring your own)']
				},
				{
					id: 'boundary',
					text: 'What should mark the boundaries?',
					options: ['Native hedge', 'Low fence', 'Flowering shrubs', 'Open and unfenced']
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
		await recalculateFollowUpCost();
	}

	async function recalculateFollowUpCost() {
		if (personas.length === 0 || followUpQuestions.length === 0) return;

		followUpCostEstimate = null; // Show loading state

		try {
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
		surveyModelUsed = null;
	}

	async function generateImage() {
		if (!winningOption || followUpTallies.length === 0) return;

		generatingImage = true;
		imageError = null;

		// Build design choices from the winning answers
		const designChoices = followUpTallies.map((tally, i) => ({
			question: followUpQuestions[i].text,
			answer: tally.tallies[0]?.[0] || 'Not specified'
		}));

		try {
			const response = await fetch(`${API_URL}/api/generate-image`, {
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

	function getModelDisplayName(modelId) {
		if (!modelId || modelId === 'sample-data') return 'Sample Data';
		const model = models.find(m => m.id === modelId);
		return model ? `${model.name}` : modelId;
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

	function downloadResults() {
		const data = {
			surveyResults,
			followUpResults,
			followUpQuestions,
			winningOption,
			totalCost,
			generatedImage,
			imagePrompt
		};

		const dataStr = JSON.stringify(data, null, 2);
		const blob = new Blob([dataStr], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `testing-space-results.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	async function loadSampleDataFile() {
		if (sampleData) return;

		loadingSampleData = true;
		try {
			const res = await fetch('/sample-data/02-testing-space-results.json');
			if (res.ok) {
				sampleData = await res.json();
			} else {
				error = 'Sample data not found. Run a survey with Live LLM first, then download the results.';
			}
		} catch (e) {
			error = 'Could not load sample data file.';
		} finally {
			loadingSampleData = false;
		}
	}

	async function runSurveyWithSampleData() {
		if (!sampleData || !sampleData.surveyResults) {
			error = 'No sample survey data available.';
			return;
		}
		if (!sampleData.modelUsed) {
			throw new Error('Sample data is missing modelUsed');
		}

		phase = 'surveying';
		surveyProgress = 0;
		surveyResults = [];
		totalCost = 0;
		surveyModelUsed = sampleData.modelUsed;

		// Simulate survey progress with delay
		await new Promise(resolve => setTimeout(resolve, 800));

		surveyResults = sampleData.surveyResults;
		// Cost is always 0 for sample data
		totalCost = 0;
		phase = 'results';

		// Set the winning option from sample data or calculate from results
		if (sampleData.winningOption) {
			winningOption = sampleData.winningOption;
		} else if (voteTallies.length > 0) {
			winningOption = voteTallies[0][0];
		}
	}

	async function runFollowUpSurveyWithSampleData() {
		if (!sampleData || !sampleData.followUpResults) {
			error = 'No sample follow-up data available.';
			return;
		}

		phase = 'followup-surveying';
		followUpResults = [];
		currentFollowUpQuestion = 0;

		// Use the follow-up questions from sample data if available
		if (sampleData.followUpQuestions) {
			followUpQuestions = sampleData.followUpQuestions;
		}

		// Simulate survey progress
		for (let i = 0; i < followUpQuestions.length; i++) {
			currentFollowUpQuestion = i + 1;
			await new Promise(resolve => setTimeout(resolve, 500));
		}

		followUpResults = sampleData.followUpResults;
		// Cost is always 0 for sample data (don't add anything)

		// Load image path from sample data
		if (!sampleData.generatedImagePath) {
			throw new Error('Sample data is missing generatedImagePath');
		}
		generatedImage = sampleData.generatedImagePath;
		imagePrompt = sampleData.imagePrompt || 'Sample visualization';

		phase = 'followup-results';
	}

	// Load sample data when switching to sample mode
	$effect(() => {
		if (useSampleData && !sampleData && !loadingSampleData) {
			loadSampleDataFile();
		}
	});
</script>

<svelte:head>
	<title>02: Testing space before it happens</title>
</svelte:head>

<nav class="nav">
	<a href="/">&larr; Back to experiments</a>
</nav>

<header class="header">
	<h1>Testing <em>space</em> before it happens</h1>
	<p class="subtitle">Experiment 02</p>
</header>

<div class="intro">
	<p class="tldr">
		<strong>TLDR:</strong> Surveying a synthetic population of 100 Londoners to test how they might respond to decisions about shared space.
	</p>

	<p>
		A <a href="https://www.standard.co.uk/homesandproperty/buying-mortgages/grand-designs-london-land-for-sale-planning-permission-developer-b1149255.html" target="_blank" rel="noopener">0.3-acre plot</a> in East London was collectively acquired by 41 neighbouring households who formed a Community Land Trust. Now they need to decide what to do with it.
	</p>

	<figure class="plot-image">
		<img src="/images/plot_1.png" alt="The plot of land in Dalston" />
		<figcaption>The site at the time of acquisition, March 2024</figcaption>
	</figure>

	<figure class="plot-image">
		<img src="/images/trust.png" alt="Satellite view showing the CLT member properties in blue surrounding the plot in green" />
		<figcaption>Some of the CLT member properties surrounding the plot (green)</figcaption>
	</figure>

	<p>
		We've generated 100 synthetic personas based on E8 postcode demographics. Can we simulate the deliberation?
	</p>
</div>

<!-- Neighbourhood Map Visualization -->
{#if households.length > 0}
	<div class="neighbourhood-section">
		<h2>The Community</h2>
		<p class="neighbourhood-intro">{households.length} households, {personas.length} residents. Click on a house to see who lives there.</p>

		<div class="neighbourhood-layout">
			<div class="neighbourhood-map">
				<!-- Central plot -->
				<div class="central-plot">
					<span class="plot-label">The Plot</span>
					<span class="plot-size">0.3 acres</span>
				</div>

				<!-- Streets and houses -->
				{#each Object.entries(streetGroups) as [streetName, streetHouseholds], streetIndex}
					<div class="street" class:street-top={streetIndex === 0} class:street-right={streetIndex === 1} class:street-bottom={streetIndex === 2} class:street-left={streetIndex === 3}>
						<div class="street-label">{streetName}</div>
						<div class="street-road"></div>
						<div class="houses-row">
							{#each streetHouseholds as household}
								<button
									class="house"
									class:selected={selectedHousehold?.id === household.id}
									class:victorian={household.address.property_type === 'Victorian terrace'}
									class:council={household.address.property_type === 'Council flat'}
									class:newbuild={household.address.property_type === 'New build'}
									onclick={() => selectHousehold(household)}
									title="{household.address.number} {household.address.street}"
								>
									<span class="house-number">{household.address.number}</span>
								</button>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			<!-- Household detail panel -->
			{#if selectedHousehold}
				<div class="household-panel">
					<button class="panel-close" onclick={closeHousehold}>&times;</button>

					<div class="panel-header">
						<h3>{selectedHousehold.address.number} {selectedHousehold.address.street}</h3>
						<div class="panel-meta">
							<span class="meta-tag">{selectedHousehold.address.property_type}</span>
							<span class="meta-tag">{selectedHousehold.tenure.replace('_', ' ')}</span>
						</div>
						<p class="panel-subtitle">{selectedHousehold.household_type.replace(/_/g, ' ')} &middot; {selectedHousehold.years_in_area} years in area</p>
					</div>

					<div class="panel-residents">
						<h4>Residents ({selectedHousehold.members.length})</h4>
						<div class="residents-list">
							{#each selectedHousehold.members as member}
								<button
									class="resident-row"
									class:selected={selectedPerson?.id === member.id}
									onclick={() => selectPerson(member, selectedHousehold)}
								>
									<div class="resident-avatar">{member.name.charAt(0)}</div>
									<div class="resident-info">
										<span class="resident-name">{member.name}</span>
										<span class="resident-details">{member.age} &middot; {member.occupation}</span>
									</div>
									<span class="resident-arrow">&rsaquo;</span>
								</button>
							{/each}
						</div>
					</div>
				</div>
			{:else}
				<div class="household-panel household-panel-empty">
					<p>Click on a house to see who lives there</p>
					<div class="legend">
						<h4>Property Types</h4>
						<div class="legend-item"><span class="legend-color victorian"></span> Victorian terrace</div>
						<div class="legend-item"><span class="legend-color council"></span> Council flat</div>
						<div class="legend-item"><span class="legend-color newbuild"></span> New build</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- Person Detail Modal -->
{#if selectedPerson}
	<div class="person-modal-backdrop" onclick={closePerson}></div>
	<div class="person-modal">
		<button class="modal-close" onclick={closePerson}>&times;</button>

		<div class="person-header">
			<h3>{selectedPerson.name}</h3>
			<p class="person-meta">{selectedPerson.age} years old &middot; {selectedPerson.gender} &middot; {selectedPerson.ethnicity}</p>
		</div>

		<div class="person-details">
			<div class="detail-row">
				<span class="detail-label">Occupation</span>
				<span class="detail-value">{selectedPerson.occupation}</span>
			</div>
			<div class="detail-row">
				<span class="detail-label">Education</span>
				<span class="detail-value">{selectedPerson.education}</span>
			</div>
			<div class="detail-row">
				<span class="detail-label">Political lean</span>
				<span class="detail-value">{selectedPerson.political_lean}</span>
			</div>
			<div class="detail-row">
				<span class="detail-label">Address</span>
				<span class="detail-value">{selectedPerson.household.address.number} {selectedPerson.household.address.street}</span>
			</div>
			<div class="detail-row">
				<span class="detail-label">Years in area</span>
				<span class="detail-value">{selectedPerson.household.years_in_area}</span>
			</div>
		</div>

		<div class="person-sketch">
			<p>{selectedPerson.personality_sketch}</p>
		</div>

		<div class="person-files">
			<h4>Profile Data Files</h4>
			{#if loadingFiles}
				<p class="loading-files">Loading files...</p>
			{:else if personFiles.length === 0}
				<p class="no-files">No files available</p>
			{:else}
				<div class="files-list">
					{#each personFiles as file}
						<details class="file-item">
							<summary>{file.name}</summary>
							<pre class="file-content">{file.content}</pre>
						</details>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

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
{/if}

{#if !loadingPersonas && personas.length > 0 && (phase === 'intro' || phase === 'estimate')}
	<div class="survey-section">
		<h2>The Survey</h2>
		<p>We have <strong>{personas.length} synthetic residents</strong> ready to vote on what should be done with the plot.</p>

		<div class="options-preview">
			<h3>The Options</h3>
			<div class="options-grid">
				{#each plotOptions as option, i}
					<div class="option-item">
						<span class="option-number">{i + 1}.</span>
						{option}
					</div>
				{/each}
			</div>
		</div>

		<div class="survey-controls">
			<div class="controls-row">
				<div class="control-group">
					<span class="control-label">Data source</span>
					<div class="toggle-buttons">
						<button
							class="toggle-btn"
							class:active={!useSampleData}
							onclick={() => useSampleData = false}
						>
							Live LLM
						</button>
						<button
							class="toggle-btn"
							class:active={useSampleData}
							onclick={() => useSampleData = true}
						>
							Sample Data
						</button>
					</div>
					{#if useSampleData && loadingSampleData}
						<span class="sample-status">Loading...</span>
					{:else if useSampleData && !sampleData}
						<span class="sample-status warning">No sample data found</span>
					{:else if useSampleData && sampleData}
						<span class="sample-status">{sampleData.surveyResults?.length || 0} responses</span>
					{/if}
				</div>

				{#if !useSampleData}
					<div class="control-group">
						<label for="model-select" class="control-label">Model</label>
						<select id="model-select" bind:value={selectedModel}>
							{#each models as model}
								<option value={model.id}>{model.name} ({model.provider})</option>
							{/each}
							{#if models.length === 0}
								<option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
							{/if}
						</select>
					</div>
				{/if}

				{#if phase === 'intro'}
					<div class="control-group control-group-action">
						{#if useSampleData}
							<button class="run-btn" onclick={runSurveyWithSampleData} disabled={!sampleData}>Run Survey</button>
						{:else}
							<button class="run-btn" onclick={estimateCost}>Get Cost Estimate</button>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if phase === 'estimate'}
			{#if costEstimate}
				<div class="estimate-card">
					<h3>Cost Estimate</h3>
					<p class="estimate-summary">
						{costEstimate.num_agents} personas &times; 1 question ({plotOptions.length} options) = <strong>{formatCost(costEstimate.total_cost)}</strong>
					</p>
					<div class="action-buttons">
						<button onclick={runSurvey} class="primary">Run Survey</button>
						<button onclick={() => { costEstimate = null; phase = 'intro'; }} class="secondary">Cancel</button>
					</div>
				</div>
			{:else}
				<p class="calculating">Calculating estimate...</p>
			{/if}
		{/if}
	</div>
{:else if phase === 'surveying'}
	<div class="survey-section">
		<h2>Survey in Progress</h2>
		<div class="survey-status">
			<div class="spinner"></div>
			<p>Surveying {personas.length} personas on their preferences...</p>
		</div>
	</div>
{:else if phase === 'results' || phase === 'followup-estimate' || phase === 'followup-surveying' || phase === 'followup-results'}
	<div class="results-section">
		<h2>Phase 1: Survey Results</h2>

		<div class="results-summary">
			<p><strong>{surveyResults.length}</strong> votes collected | Model: <strong>{getModelDisplayName(surveyModelUsed)}</strong> | Cost: <strong>{formatCost(totalCost)}</strong></p>
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
								{#if response.justification}
									<span class="response-justification">"{response.justification}"</span>
								{/if}
							</div>
						{/each}
					</div>
				</details>
			</div>

			{#if phase === 'results'}
			<div class="followup-section">
				<h2>Phase 2: Design Decisions</h2>
				<p>The community has chosen <strong>"{winningOption}"</strong>. Now let's ask 3 follow-up questions to refine the design.</p>
				<button onclick={generateFollowUpQuestions}>Generate Follow-up Questions</button>
			</div>
		{/if}
		{/if}
	</div>
{/if}

{#if phase === 'followup-estimate' && followUpQuestions.length > 0}
	<div class="survey-section">
		<h2>Follow-up Survey{useSampleData ? '' : ' Cost Estimate'}</h2>

		<div class="followup-questions-preview">
			<h3>3 Design Questions</h3>
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

		{#if useSampleData}
			<div class="action-buttons">
				<button onclick={runFollowUpSurveyWithSampleData} class="primary" disabled={!sampleData?.followUpResults}>Run Follow-up Survey (Sample Data)</button>
				<button onclick={() => (phase = 'results')} class="secondary">Back to Results</button>
			</div>
		{:else}
			<div class="control-group">
				<label for="followup-model-select" class="control-label">Model</label>
				<select id="followup-model-select" bind:value={selectedModel}>
					{#each models as model}
						<option value={model.id}>{model.name} ({model.provider})</option>
					{/each}
					{#if models.length === 0}
						<option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
					{/if}
				</select>
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
		{/if}
	</div>
	{/if}

	{#if phase === 'followup-surveying'}
	<div class="survey-section">
		<h2>Phase 2: Survey in Progress</h2>
		<div class="survey-status">
			<div class="spinner"></div>
			<p>Asking {personas.length} personas about: {followUpQuestions[currentFollowUpQuestion - 1]?.text || ''}</p>
			<p class="survey-status-detail">Question {currentFollowUpQuestion} of {followUpQuestions.length}</p>
		</div>
	</div>
	{/if}

	{#if phase === 'followup-results'}
	<div class="results-section">
		<h2>Phase 2: Design Survey Results</h2>

		<div class="results-summary">
			<p>
				<strong>{followUpResults.length}</strong> total responses across {followUpQuestions.length} questions | Model: <strong>{getModelDisplayName(surveyModelUsed)}</strong> | Cost: <strong>{formatCost(totalCost)}</strong>
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
				<details class="followup-individual-responses">
					<summary>Show individual responses</summary>
					<div class="responses-list">
						{#each followUpResults.filter(r => r.question_index === i) as response}
							{@const persona = personas.find((p) => p.id === response.persona_id)}
							<div class="response-item">
								<span class="response-name">{response.persona_name}</span>
								<span class="response-meta">{persona?.age || '?'}, {persona?.occupation || '?'}</span>
								<span class="response-vote">{response.response}</span>
								{#if response.justification}
									<span class="response-justification">"{response.justification}"</span>
								{/if}
							</div>
						{/each}
					</div>
				</details>
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
				<button onclick={generateImage} class="primary generate-btn">
					Generate Image
				</button>
			{:else if generatingImage}
				<div class="generating-status">
					<div class="spinner"></div>
					<p>Generating the community's vision...</p>
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
							<img src={generatedImage.startsWith('/') ? generatedImage : `data:image/png;base64,${generatedImage}`} alt="Generated design" />
						</div>
					</div>
				</div>

				<details class="prompt-details">
					<summary>View generation prompt</summary>
					<pre class="prompt-text">{imagePrompt}</pre>
				</details>

				<div class="action-buttons">
					<button onclick={generateImage} class="secondary">Regenerate Image</button>
				</div>
			{/if}
		</div>

		<div class="action-buttons final-actions">
			<button onclick={reset} class="secondary">Start Over</button>
			{#if !useSampleData}
				<button onclick={downloadResults} class="secondary download-btn">Download Results</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	.header {
		margin-bottom: 0.5rem;
	}

	.survey-controls {
		background: #f8f8f8;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		padding: 1.25rem 1.5rem;
		margin-top: 1.5rem;
	}

	.controls-row {
		display: flex;
		align-items: flex-end;
		gap: 2rem;
		flex-wrap: wrap;
	}

	.control-group {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.control-group-action {
		margin-left: auto;
	}

	.control-label {
		font-size: 0.75rem;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		font-weight: 500;
	}

	.toggle-buttons {
		display: flex;
		border: 1px solid #ccc;
		border-radius: 4px;
		overflow: hidden;
	}

	.toggle-btn {
		background: white;
		color: #555;
		border: none;
		border-radius: 0;
		padding: 0.5rem 1rem;
		font-size: 0.9rem;
		margin: 0;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.toggle-btn:not(:last-child) {
		border-right: 1px solid #ccc;
	}

	.toggle-btn:hover:not(.active) {
		background: #f0f0f0;
	}

	.toggle-btn.active {
		background: var(--accent);
		color: white;
	}

	.sample-status {
		font-size: 0.8rem;
		color: #666;
		margin-top: 0.25rem;
	}

	.sample-status.warning {
		color: #b45309;
	}

	.control-group select {
		font-family: inherit;
		font-size: 0.9rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid #ccc;
		border-radius: 4px;
		background: white;
		min-width: 200px;
	}

	.run-btn {
		background: var(--accent);
		color: white;
		padding: 0.5rem 1.5rem;
		font-size: 0.95rem;
		margin: 0;
		white-space: nowrap;
	}

	.run-btn:hover:not(:disabled) {
		background: #6b1010;
	}

	.run-btn:disabled {
		background: #ccc;
		cursor: not-allowed;
	}

	.download-btn {
		background: #2563eb;
	}

	.download-btn:hover {
		background: #1d4ed8;
	}

	@media (max-width: 600px) {
		.controls-row {
			flex-direction: column;
			align-items: stretch;
			gap: 1rem;
		}

		.control-group-action {
			margin-left: 0;
		}

		.run-btn {
			width: 100%;
		}
	}

	.intro {
		margin-bottom: 2rem;
	}

	.intro p {
		line-height: 1.7;
	}

	.intro .tldr {
		background: #f5f5f5;
		padding: 1rem 1.25rem;
		border-radius: 4px;
		font-style: italic;
		color: #555;
	}

	.intro .tldr strong {
		font-style: normal;
		color: #333;
	}

	.intro h2 {
		margin-top: 2rem;
		margin-bottom: 0.75rem;
		font-size: 1.3rem;
	}

	.plot-image {
		margin: 2rem 0;
		padding: 0;
		text-align: center;
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


	.estimate-card {
		background: #f9f9f9;
		border-left: 3px solid var(--accent);
		padding: 1.5rem;
		margin: 1.5rem 0;
	}

	.estimate-card h3 {
		margin-top: 0;
		margin-bottom: 0.5rem;
		font-size: 1rem;
	}

	.estimate-summary {
		font-size: 1.1rem;
		margin-bottom: 1rem;
	}

	.calculating {
		color: #666;
		font-style: italic;
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

	.survey-status {
		text-align: center;
		padding: 2rem;
	}

	.survey-status p {
		margin: 0.5rem 0;
	}

	.survey-status-detail {
		color: #888;
		font-size: 0.9rem;
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
		grid-template-rows: auto auto;
		gap: 0.25rem 1rem;
		padding: 0.75rem 0;
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

	.response-justification {
		grid-column: 1 / -1;
		color: #555;
		font-style: italic;
		font-size: 0.85rem;
		padding-left: 0.5rem;
		border-left: 2px solid #ddd;
		margin-top: 0.25rem;
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

	.followup-individual-responses {
		margin-top: 1rem;
	}

	.followup-individual-responses summary {
		font-size: 0.9rem;
	}

	.followup-individual-responses .responses-list {
		max-height: 300px;
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

	.before-after-preview {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 1.5rem;
		align-items: center;
		justify-items: center;
		margin: 2rem 0;
	}

	.before-after-images {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 2rem;
		align-items: start;
		justify-items: center;
		margin: 2rem auto;
		max-width: 900px;
	}

	.preview-image,
	.ba-image {
		text-align: center;
		width: 100%;
	}

	.preview-image img,
	.ba-image img {
		width: 100%;
		max-width: 400px;
		height: auto;
		aspect-ratio: 4 / 3;
		object-fit: cover;
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
			grid-template-rows: auto;
			gap: 0.25rem;
		}

		.response-justification {
			padding-left: 0;
			border-left: none;
			padding-top: 0.25rem;
			border-top: 1px solid #eee;
		}

		.voter-breakdown {
			grid-template-columns: 1fr;
		}

		.before-after-preview {
			grid-template-columns: 1fr;
			gap: 1rem;
		}

		.before-after-images {
			grid-template-columns: 1fr;
			gap: 1.5rem;
		}

		.arrow {
			transform: rotate(90deg);
		}
	}

	/* Neighbourhood Map Visualization */
	.neighbourhood-section {
		margin: 3rem 0;
	}

	.neighbourhood-section h2 {
		margin-bottom: 0.5rem;
	}

	.neighbourhood-intro {
		color: #666;
		margin-bottom: 1.5rem;
	}

	.neighbourhood-layout {
		display: grid;
		grid-template-columns: 1fr 320px;
		gap: 2rem;
		align-items: start;
	}

	.neighbourhood-map {
		background: #f0f4f0;
		border-radius: 8px;
		padding: 2rem;
		position: relative;
		min-height: 500px;
		display: grid;
		grid-template-rows: auto 1fr auto;
		grid-template-columns: auto 1fr auto;
		gap: 0.5rem;
	}

	.central-plot {
		grid-row: 2;
		grid-column: 2;
		background: linear-gradient(135deg, #90c695 0%, #6b9b6e 100%);
		border: 2px solid #5a8a5d;
		border-radius: 4px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		color: white;
		text-shadow: 0 1px 2px rgba(0,0,0,0.3);
	}

	.plot-label {
		font-weight: 600;
		font-size: 1.1rem;
	}

	.plot-size {
		font-size: 0.85rem;
		opacity: 0.9;
	}

	.street {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}

	.street-top {
		grid-row: 1;
		grid-column: 2;
	}

	.street-right {
		grid-row: 2;
		grid-column: 3;
		flex-direction: row;
	}

	.street-bottom {
		grid-row: 3;
		grid-column: 2;
		flex-direction: column-reverse;
	}

	.street-left {
		grid-row: 2;
		grid-column: 1;
		flex-direction: row-reverse;
	}

	.street-label {
		font-size: 0.7rem;
		color: #666;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		text-align: center;
		white-space: nowrap;
	}

	.street-right .street-label,
	.street-left .street-label {
		writing-mode: vertical-rl;
		text-orientation: mixed;
	}

	.street-left .street-label {
		transform: rotate(180deg);
	}

	.street-road {
		background: #d4d4d4;
		height: 4px;
		border-radius: 2px;
	}

	.street-right .street-road,
	.street-left .street-road {
		width: 4px;
		height: auto;
		flex: 1;
	}

	.houses-row {
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.street-right .houses-row,
	.street-left .houses-row {
		flex-direction: column;
	}

	.house {
		width: 36px;
		height: 36px;
		border: 2px solid #8b6914;
		border-radius: 3px;
		background: #d4a84b;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 2px;
		transition: all 0.15s ease;
		position: relative;
	}

	.house:hover {
		transform: scale(1.15);
		z-index: 10;
	}

	.house.selected {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px rgba(139, 0, 0, 0.3);
		transform: scale(1.15);
		z-index: 10;
	}

	.house.victorian {
		background: #d4a84b;
		border-color: #8b6914;
	}

	.house.council {
		background: #a0b8c8;
		border-color: #5d7a8c;
	}

	.house.newbuild {
		background: #c9b8d4;
		border-color: #7d6b8a;
	}

	.house-number {
		font-size: 0.6rem;
		font-weight: 600;
		color: rgba(0,0,0,0.7);
		line-height: 1;
	}


	/* Household Panel */
	.household-panel {
		background: #fafafa;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		padding: 1.5rem;
		position: relative;
	}

	.household-panel-empty {
		color: #888;
		text-align: center;
		padding: 2rem 1.5rem;
	}

	.household-panel-empty p {
		margin-bottom: 2rem;
		font-style: italic;
	}

	.legend {
		text-align: left;
	}

	.legend h4 {
		font-size: 0.85rem;
		margin-bottom: 0.75rem;
		color: #666;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8rem;
		margin-bottom: 0.4rem;
		color: #555;
	}

	.legend-color {
		width: 20px;
		height: 20px;
		border-radius: 3px;
		border: 2px solid;
	}

	.legend-color.victorian {
		background: #d4a84b;
		border-color: #8b6914;
	}

	.legend-color.council {
		background: #a0b8c8;
		border-color: #5d7a8c;
	}

	.legend-color.newbuild {
		background: #c9b8d4;
		border-color: #7d6b8a;
	}

	.panel-close {
		position: absolute;
		top: 0.75rem;
		right: 0.75rem;
		background: none;
		border: none;
		font-size: 1.25rem;
		color: #999;
		cursor: pointer;
		padding: 0;
		line-height: 1;
		margin: 0;
	}

	.panel-close:hover {
		color: var(--accent);
		background: none;
	}

	.panel-header {
		margin-bottom: 1.25rem;
	}

	.panel-header h3 {
		font-size: 1.1rem;
		margin-bottom: 0.4rem;
	}

	.panel-meta {
		display: flex;
		gap: 0.4rem;
		margin-bottom: 0.4rem;
	}

	.meta-tag {
		font-size: 0.7rem;
		background: #e8e8e8;
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
		color: #555;
		text-transform: capitalize;
	}

	.panel-subtitle {
		font-size: 0.85rem;
		color: #666;
		margin: 0;
		text-transform: capitalize;
	}

	.panel-residents h4 {
		font-size: 0.9rem;
		margin-bottom: 0.75rem;
		color: #444;
	}

	.residents-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.resident-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		background: white;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		padding: 0.6rem 0.75rem;
		cursor: pointer;
		text-align: left;
		transition: all 0.15s ease;
	}

	.resident-row:hover {
		border-color: var(--accent);
		background: #fff8f8;
	}

	.resident-row.selected {
		border-color: var(--accent);
		background: var(--accent);
		color: white;
	}

	.resident-avatar {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: #e0e0e0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: 600;
		font-size: 0.9rem;
		flex-shrink: 0;
	}

	.resident-row.selected .resident-avatar {
		background: rgba(255,255,255,0.3);
	}

	.resident-info {
		flex: 1;
		min-width: 0;
	}

	.resident-name {
		display: block;
		font-weight: 500;
		font-size: 0.9rem;
		margin-bottom: 0.1rem;
	}

	.resident-details {
		display: block;
		font-size: 0.75rem;
		color: #888;
		text-transform: capitalize;
	}

	.resident-row.selected .resident-details {
		color: rgba(255,255,255,0.8);
	}

	.resident-arrow {
		font-size: 1.2rem;
		color: #ccc;
	}

	.resident-row.selected .resident-arrow {
		color: rgba(255,255,255,0.8);
	}

	@media (max-width: 800px) {
		.neighbourhood-layout {
			grid-template-columns: 1fr;
		}

		.household-panel {
			order: -1;
		}
	}

	/* Person Modal */
	.person-modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 1000;
	}

	.person-modal {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: white;
		border-radius: 8px;
		padding: 2rem;
		max-width: 600px;
		width: 90%;
		max-height: 85vh;
		overflow-y: auto;
		z-index: 1001;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
	}

	.modal-close {
		position: absolute;
		top: 1rem;
		right: 1rem;
		background: none;
		border: none;
		font-size: 1.5rem;
		color: #666;
		cursor: pointer;
		padding: 0;
		line-height: 1;
		margin: 0;
	}

	.modal-close:hover {
		color: var(--accent);
		background: none;
	}

	.person-header {
		margin-bottom: 1.5rem;
	}

	.person-header h3 {
		margin-bottom: 0.25rem;
		font-size: 1.5rem;
	}

	.person-meta {
		color: #666;
		font-size: 0.95rem;
		margin: 0;
	}

	.person-details {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem 2rem;
		margin-bottom: 1.5rem;
	}

	.detail-row {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.detail-label {
		font-size: 0.75rem;
		color: #888;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.detail-value {
		font-size: 0.95rem;
		text-transform: capitalize;
	}

	.person-sketch {
		background: #f5f5f5;
		padding: 1rem;
		border-radius: 4px;
		margin-bottom: 1.5rem;
	}

	.person-sketch p {
		margin: 0;
		font-style: italic;
		color: #555;
		line-height: 1.6;
	}

	.person-files h4 {
		font-size: 1rem;
		margin-bottom: 0.75rem;
		color: #333;
	}

	.loading-files,
	.no-files {
		color: #888;
		font-style: italic;
	}

	.files-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.file-item {
		border: 1px solid #e0e0e0;
		border-radius: 4px;
	}

	.file-item summary {
		padding: 0.6rem 1rem;
		cursor: pointer;
		font-family: 'SF Mono', 'Consolas', monospace;
		font-size: 0.85rem;
		background: #fafafa;
		border-radius: 4px;
	}

	.file-item[open] summary {
		border-bottom: 1px solid #e0e0e0;
		border-radius: 4px 4px 0 0;
	}

	.file-content {
		padding: 1rem;
		margin: 0;
		font-size: 0.8rem;
		line-height: 1.5;
		white-space: pre-wrap;
		word-break: break-word;
		background: white;
		max-height: 300px;
		overflow-y: auto;
	}

	@media (max-width: 500px) {
		.person-details {
			grid-template-columns: 1fr;
		}
	}
</style>
