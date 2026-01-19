<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';

	const API_URL = '';

	// API key status
	let keyStatus = $state({
		openai: false,
		anthropic: false,
		gemini: false,
		has_llm_key: false
	});
	let showKeyModal = $state(false);
	let checkingKeys = $state(true);
	let savingKeys = $state(false);
	let saveError = $state(null);
	let apiAvailable = $state(false);

	// Form inputs
	let openaiKey = $state('');
	let anthropicKey = $state('');
	let geminiKey = $state('');

	onMount(async () => {
		if (!browser) return;
		await checkApiKeys();
	});

	async function checkApiKeys() {
		checkingKeys = true;
		try {
			const res = await fetch(`${API_URL}/api/keys/status`);
			if (res.ok) {
				apiAvailable = true;
				keyStatus = await res.json();
			}
		} catch (e) {
			// API not running - don't show modal
			apiAvailable = false;
			console.log('API not available');
		} finally {
			checkingKeys = false;
		}
	}

	async function saveKeys() {
		savingKeys = true;
		saveError = null;

		try {
			const res = await fetch(`${API_URL}/api/keys/set`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					openai_key: openaiKey || null,
					anthropic_key: anthropicKey || null,
					gemini_key: geminiKey || null
				})
			});

			if (res.ok) {
				keyStatus = await res.json();
				if (keyStatus.has_llm_key) {
					showKeyModal = false;
					openaiKey = '';
					anthropicKey = '';
					geminiKey = '';
				} else {
					saveError = 'Please provide at least one LLM API key (OpenAI or Anthropic)';
				}
			} else {
				saveError = 'Failed to save API keys';
			}
		} catch (e) {
			saveError = 'Could not connect to API server';
		} finally {
			savingKeys = false;
		}
	}

	function openKeySettings() {
		showKeyModal = true;
	}
</script>

<svelte:head>
	<title>Weekend adventures in artificial societies...</title>
</svelte:head>

{#if showKeyModal}
	<div class="modal-backdrop" onclick={() => showKeyModal = false}></div>
	<div class="modal">
		<div class="modal-header">
			<h2>API Keys {keyStatus.has_llm_key ? 'Settings' : 'Required'}</h2>
			<button class="modal-close" onclick={() => showKeyModal = false}>&times;</button>
		</div>

		<p class="modal-intro">
			To run experiments with live LLM responses, you need to configure API keys.
			Keys are stored in memory only and will be cleared when the server restarts.
		</p>

		<div class="key-section">
			<h3>LLM Provider <span class="required">(at least one required)</span></h3>
			<p class="key-hint">Add one or both of these keys to enable persona generation and surveys.</p>

			<div class="key-input-group">
				<label for="openai-key">
					OpenAI API Key
					{#if keyStatus.openai}<span class="key-status configured">Configured</span>{/if}
				</label>
				<input
					id="openai-key"
					type="password"
					bind:value={openaiKey}
					placeholder={keyStatus.openai ? '••••••••' : 'sk-...'}
				/>
			</div>

			<div class="key-input-group">
				<label for="anthropic-key">
					Anthropic API Key
					{#if keyStatus.anthropic}<span class="key-status configured">Configured</span>{/if}
				</label>
				<input
					id="anthropic-key"
					type="password"
					bind:value={anthropicKey}
					placeholder={keyStatus.anthropic ? '••••••••' : 'sk-ant-...'}
				/>
			</div>
		</div>

		<div class="key-section">
			<h3>Image Generation <span class="optional">(optional)</span></h3>
			<p class="key-hint">Required if you want to generate visualizations of survey results.</p>

			<div class="key-input-group">
				<label for="gemini-key">
					Google Gemini API Key
					{#if keyStatus.gemini}<span class="key-status configured">Configured</span>{/if}
				</label>
				<input
					id="gemini-key"
					type="password"
					bind:value={geminiKey}
					placeholder={keyStatus.gemini ? '••••••••' : 'AIza...'}
				/>
			</div>
		</div>

		{#if saveError}
			<p class="error">{saveError}</p>
		{/if}

		<div class="modal-actions">
			<button onclick={saveKeys} disabled={savingKeys} class="primary">
				{savingKeys ? 'Saving...' : 'Save Keys'}
			</button>
			{#if keyStatus.has_llm_key}
				<button onclick={() => showKeyModal = false} class="secondary">Cancel</button>
			{/if}
		</div>

	</div>
{/if}

<h1>Weekend adventures in artificial societies...</h1>

<p class="intro">
	These are some of the early outputs from my initial experiments asking language
	models to simulate human populations and seeing what happens. This experimentation
	gave me a much greater appreciation of the art involved. Whilst it's possible to
	vibecode a community of agents in a weekend, it's easy to underestimate how
	challenging it can be to design useful experiments and counter the biases within LLMs.
</p>

<p>
	There's clearly an opportunity for building moats around well curated datasets
	of personas and hard-earned forward-deployed experience in the emerging art of silicon sampling.
</p>

<hr />

<h2>Experiments</h2>

<ul class="experiment-list">
	<li>
		<span class="experiment-number">01</span>
		<a href="/experiments/01-random-person-generator">Random person generator</a>
	</li>
	<li>
		<span class="experiment-number">02</span>
		<a href="/experiments/02-testing-space-before-it-happens">Testing <em>space</em> before it happens</a>
	</li>
	<li class="upcoming">
		<span class="experiment-number">03</span>
		<span class="experiment-title" data-tooltip="Agents that interact, remember, and maintain state. After each step, the conversation forks—a separate instance reports metrics like mood, trust, stress, while the original continues unaware. Provides time series analysis of emotion at population level.">Fourth Wall</span>
	</li>
</ul>

<hr />

<div class="settings-section">
	<button class="settings-btn" onclick={openKeySettings} disabled={!apiAvailable && !checkingKeys}>
		API Key Settings
		{#if apiAvailable && !keyStatus.has_llm_key && !checkingKeys}
			<span class="warning-badge">!</span>
		{/if}
	</button>
	<span class="settings-status">
		{#if checkingKeys}
			Checking...
		{:else if !apiAvailable}
			API server not running
		{:else if keyStatus.has_llm_key}
			{#if keyStatus.openai && keyStatus.anthropic}
				OpenAI + Anthropic configured
			{:else if keyStatus.openai}
				OpenAI configured
			{:else if keyStatus.anthropic}
				Anthropic configured
			{/if}
			{#if keyStatus.gemini}
				 + Gemini
			{/if}
		{:else}
			No API keys configured
		{/if}
	</span>
</div>

<style>
	.settings-section {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-top: 1rem;
	}

	.settings-btn {
		background: #333;
		color: white;
		border: 1px solid #333;
		padding: 0.5rem 1rem;
		font-size: 0.9rem;
		cursor: pointer;
		border-radius: 4px;
		position: relative;
		font-weight: 500;
	}

	.settings-btn:hover:not(:disabled) {
		background: #444;
		border-color: #444;
	}

	.settings-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.warning-badge {
		position: absolute;
		top: -6px;
		right: -6px;
		background: #dc2626;
		color: white;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: bold;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.settings-status {
		font-size: 0.85rem;
		color: #666;
		display: flex;
		align-items: center;
		line-height: 1;
	}

	/* Modal styles */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 1000;
	}

	.modal {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: white;
		border-radius: 8px;
		padding: 2rem;
		max-width: 500px;
		width: 90%;
		max-height: 90vh;
		overflow-y: auto;
		z-index: 1001;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
	}

	.modal-header h2 {
		margin: 0;
		font-size: 1.4rem;
	}

	.modal-close {
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
		color: #333;
		background: none;
	}

	.modal-intro {
		color: #555;
		font-size: 0.95rem;
		margin-bottom: 1.5rem;
		line-height: 1.5;
	}

	.key-section {
		margin-bottom: 1.5rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid #eee;
	}

	.key-section:last-of-type {
		border-bottom: none;
		padding-bottom: 0;
	}

	.key-section h3 {
		margin: 0 0 0.25rem 0;
		font-size: 1rem;
	}

	.required {
		color: #dc2626;
		font-weight: normal;
		font-size: 0.85rem;
	}

	.optional {
		color: #666;
		font-weight: normal;
		font-size: 0.85rem;
	}

	.key-hint {
		color: #666;
		font-size: 0.85rem;
		margin: 0 0 1rem 0;
	}

	.key-input-group {
		margin-bottom: 1rem;
	}

	.key-input-group:last-child {
		margin-bottom: 0;
	}

	.key-input-group label {
		display: block;
		font-size: 0.9rem;
		font-weight: 500;
		margin-bottom: 0.4rem;
	}

	.key-status {
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		border-radius: 3px;
		margin-left: 0.5rem;
	}

	.key-status.configured {
		background: #dcfce7;
		color: #166534;
	}

	.key-input-group input {
		width: 100%;
		padding: 0.6rem 0.75rem;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-family: monospace;
		font-size: 0.9rem;
	}

	.key-input-group input:focus {
		outline: none;
		border-color: var(--accent, #8b0000);
		box-shadow: 0 0 0 2px rgba(139, 0, 0, 0.1);
	}

	.error {
		color: #dc2626;
		font-size: 0.9rem;
		margin-bottom: 1rem;
	}

	.modal-actions {
		display: flex;
		gap: 1rem;
		margin-top: 1.5rem;
	}

	.modal-actions button {
		padding: 0.6rem 1.5rem;
		border: none;
		border-radius: 4px;
		font-size: 0.95rem;
		cursor: pointer;
	}

	.modal-actions button.primary {
		background: var(--accent, #8b0000);
		color: white;
	}

	.modal-actions button.primary:hover:not(:disabled) {
		background: #6b0000;
	}

	.modal-actions button.primary:disabled {
		background: #ccc;
		cursor: not-allowed;
	}

	.modal-actions button.secondary {
		background: #f5f5f5;
		color: #333;
		border: 1px solid #ddd;
	}

	.modal-actions button.secondary:hover {
		background: #eee;
	}
</style>
