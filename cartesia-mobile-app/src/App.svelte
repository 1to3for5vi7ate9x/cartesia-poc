<script lang="ts">
  import { onMount } from 'svelte'; // Import onMount
  import { getClientMetrics } from './lib/client-metrics';
  // Import more queue functions
  import { addRequestToQueue, getAllQueuedRequests, removeRequestFromQueue } from './lib/request-queue';

  let query: string = '';
  let result: string = '';
  let isLoading: boolean = false;
  let error: string | null = null;

  // --- PWA Install Prompt Logic ---
  let deferredPrompt: Event | null = null; // To store the install prompt event
  let showInstallButton = false;

  async function handleInstallClick() {
    if (!deferredPrompt) {
      console.log("Install prompt not available.");
      return;
    }
    // Show the install prompt
    (deferredPrompt as any).prompt();
    // Wait for the user to respond to the prompt
    const { outcome } = await (deferredPrompt as any).userChoice;
    console.log(`User response to the install prompt: ${outcome}`);
    // We've used the prompt, reset it
    deferredPrompt = null;
    showInstallButton = false;
  }
  // --- End PWA Install Prompt Logic ---


  async function handleSubmit() {
    if (!query.trim()) return;

    isLoading = true;
    error = null;
    result = '';

    const apiUrl = 'http://localhost:7842/api/process-request';

    try {
      const clientMetrics = await getClientMetrics();
      console.log("Client Metrics:", clientMetrics);

      if (navigator.onLine) {
        // --- Online: Send request directly ---
        console.log("Browser online, sending request directly.");
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query,
            client_metrics: clientMetrics
          }),
        });

        if (!response.ok) {
          let errorMsg = `HTTP error! Status: ${response.status}`;
          try {
            const errorData = await response.json();
            errorMsg += ` - ${errorData.error || 'Unknown server error'}`;
          } catch (e) { /* Ignore */ }
          throw new Error(errorMsg);
        }

        const data = await response.json();
        result = data.result || 'No result received from server.';

      } else {
        // --- Offline: Add request to queue ---
        console.log("Browser offline, adding request to queue.");
        await addRequestToQueue({
          query: query,
          client_metrics: clientMetrics,
          apiUrl: apiUrl // Store the URL for later processing
        });
        result = `You are offline. Request for '${query}' has been queued.`;
        // Optionally provide feedback that it's queued
      }

    } catch (err: any) {
      console.error('Error during submit:', err);
      // Check if the error is likely due to being offline after the initial check
      if (!navigator.onLine && err instanceof TypeError && err.message.includes('Failed to fetch')) {
         console.log("Fetch failed, likely offline. Attempting to queue request.");
         try {
            // Need client metrics again if fetch failed before getting them
            const clientMetrics = await getClientMetrics();
            await addRequestToQueue({
              query: query,
              client_metrics: clientMetrics,
              apiUrl: apiUrl
            });
            result = `You appear to be offline. Request for '${query}' has been queued.`;
            error = null; // Clear the fetch error as we queued it
         } catch (queueError: any) {
             console.error("Error adding request to queue after fetch failure:", queueError);
             error = `Offline and failed to queue request: ${queueError.message}`;
         }
      } else {
        // Handle other errors (e.g., server errors when online)
        error = err.message || 'An unexpected error occurred.';
      }
    } finally {
      isLoading = false;
      // query = ''; // Optionally clear input after submit
    }
  }

  // --- Queue Processing Logic ---
  let isProcessingQueue = false;

  async function processQueue() {
    if (isProcessingQueue || !navigator.onLine) {
      console.log("Queue processing skipped (already running or offline).");
      return;
    }
    isProcessingQueue = true;
    console.log("Checking offline request queue...");

    try {
      const queuedRequests = await getAllQueuedRequests();
      if (queuedRequests.length === 0) {
        console.log("Queue is empty.");
        return;
      }

      console.log(`Processing ${queuedRequests.length} queued requests...`);
      result = `Processing ${queuedRequests.length} queued requests...`; // Update UI

      for (const req of queuedRequests) {
        if (req.id === undefined) continue; // Skip if ID is missing (shouldn't happen)

        console.log(`Attempting to send queued request ID: ${req.id}`, req);
        try {
          const response = await fetch(req.apiUrl, { // Use stored URL
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              query: req.query,
              client_metrics: req.client_metrics
            }),
          });

          if (!response.ok) {
            // Handle potential errors during queue processing
            // Decide if the request should be retried or discarded
            console.error(`Error processing queued request ID ${req.id}: Status ${response.status}`);
            // For simplicity, we'll just log the error and remove it.
            // A more robust implementation might retry or keep it.
          } else {
             const data = await response.json();
             console.log(`Successfully processed queued request ID ${req.id}:`, data.result);
             // Optionally update UI with the result of the last processed item
             result = `Processed queued: ${data.result}`;
          }
          
          // Remove from queue regardless of success/failure for this simple example
          await removeRequestFromQueue(req.id);

        } catch (fetchError) {
          console.error(`Network or fetch error processing queued request ID ${req.id}:`, fetchError);
          // Keep the request in the queue if the network fails during processing
          break; // Stop processing the queue if one fails due to network
        }
      }
      console.log("Finished processing queue.");
      // Optionally update UI after finishing
      // result = "Finished processing offline queue.";

    } catch (dbError) {
      console.error("Error accessing request queue:", dbError);
      result = "Error processing offline queue.";
    } finally {
      isProcessingQueue = false;
    }
  }

  // Run queue processing when the app mounts and when it comes online
  onMount(() => {
    // Check queue on initial load
    processQueue();

    // Listen for online event
    window.addEventListener('online', processQueue);

    // --- PWA Install Prompt Listener ---
    window.addEventListener('beforeinstallprompt', (e) => {
      // Prevent the mini-infobar from appearing on mobile
      e.preventDefault();
      // Stash the event so it can be triggered later.
      deferredPrompt = e;
      // Update UI notify the user they can install the PWA
      showInstallButton = true;
      console.log('`beforeinstallprompt` event was fired.');
    });

    window.addEventListener('appinstalled', () => {
      // Log install to analytics or console
      console.log('PWA was installed');
      // Hide the install button
      showInstallButton = false;
      deferredPrompt = null;
    });
    // --- End PWA Install Prompt Listener ---

    // Cleanup listeners on component destroy
    return () => {
      window.removeEventListener('online', processQueue);
      // Note: No need to remove 'beforeinstallprompt' or 'appinstalled' listeners typically
    };
  });
  // --- End Queue Processing Logic ---

</script>

<main class="app-container">
  <header>
    <h1>Cartesia Mobile App</h1>
    {#if showInstallButton}
      <button class="install-button" on:click={handleInstallClick}>
        Install App
      </button>
    {/if}
  </header>

  <section class="query-section">
    <form on:submit|preventDefault={handleSubmit}>
      <input
        type="text"
        bind:value={query}
        placeholder="Ask something (e.g., 'Weather in London')"
        aria-label="User query input"
        disabled={isLoading}
      />
      <button type="submit" disabled={isLoading}>
        {#if isLoading}
          Processing...
        {:else}
          Send
        {/if}
      </button>
    </form>
  </section>

  <section class="results-section">
    {#if isLoading}
      <p class="loading">Loading...</p>
    {:else if error}
      <p class="error">Error: {error}</p>
    {:else if result}
      <p class="result">{result}</p>
    {:else}
      <p class="placeholder">Results will appear here.</p>
    {/if}
  </section>

</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
      Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    background-color: #f4f4f9;
    color: #333;
  }

  .app-container {
    max-width: 600px;
    margin: 0 auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    min-height: 100vh; /* Ensure it takes full viewport height */
    box-sizing: border-box;
  }

  header {
    text-align: center;
    margin-bottom: 1.5rem;
    color: #4a4a4a;
    position: relative; /* Needed for absolute positioning of button if desired */
  }

  .install-button {
    /* Basic styling - adjust as needed */
    /* Example: position top-right */
    /* position: absolute;
    top: 1rem;
    right: 1rem; */
    /* Example: place below header */
    display: block;
    margin: 0.5rem auto 1rem; /* Center below header */
    padding: 0.5rem 1rem;
    background-color: #28a745; /* Green */
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .install-button:hover {
    background-color: #218838;
  }

  .query-section form {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
  }

  .query-section input[type="text"] {
    flex-grow: 1;
    padding: 0.8rem 1rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 1rem;
  }

  .query-section button {
    padding: 0.8rem 1.5rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .query-section button:hover:not(:disabled) {
    background-color: #0056b3;
  }

   .query-section button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }

  .results-section {
    background-color: #fff;
    padding: 1rem;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    min-height: 100px; /* Give it some initial height */
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .loading, .error, .result, .placeholder {
    margin: 0;
  }

  .loading {
    color: #888;
  }

  .error {
    color: #dc3545;
    font-weight: bold;
  }

  .result {
    color: #28a745;
  }

  .placeholder {
    color: #aaa;
  }

  /* Basic responsiveness */
  @media (max-width: 600px) {
    .app-container {
      padding: 0.5rem;
    }
    .query-section form {
      flex-direction: column;
    }
    .query-section button {
      width: 100%;
    }
  }
</style>
