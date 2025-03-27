# Mobile Web App with On-Device Cartesia SSM - Plan

## 1. Project Goal

To create a Progressive Web App (PWA) installable on Android and iOS devices. This app will utilize Cartesia's State Space Model (SSM) technology, ideally running locally or interacting with a local component, to perform simple, context-aware tasks initiated by the user (e.g., "What's the weather in London?").

## 2. Core Requirements

*   **Platform:** Mobile-first Web Application (PWA) for cross-platform compatibility and installability.
*   **Core Technology:** Cartesia SSM for task execution.
*   **Execution Mode:** Prioritize on-device execution or interaction with a local SSM instance if feasible. If not, fall back to interacting with a backend API (like the existing Flask server or Cartesia's cloud API).
*   **Functionality:**
    *   User input (text or potentially voice).
    *   SSM processing of the input to understand intent and extract parameters (e.g., task="weather", location="London").
    *   Execution of the identified task (e.g., calling a weather API).
    *   Displaying results to the user.
    *   PWA features: Installability, offline support (basic shell).
*   **Example Task:** Fetching and displaying current weather information.

## 3. Proposed Technology Stack

*   **Frontend Framework:** React, Vue, or Svelte (Choose one based on team familiarity and preference. Svelte might be good for performance on mobile).
*   **Styling:** Tailwind CSS or standard CSS/SCSS.
*   **PWA:** Workbox for service worker generation, standard `manifest.json`.
*   **State Management:** Context API (React), Pinia (Vue), Svelte Stores, or Zustand.
*   **SSM Integration:**
    *   **Option A (Ideal - On-Device):** Investigate if Cartesia provides a JavaScript library or WebAssembly (WASM) build of the SSM suitable for running directly in the browser. This is the most complex but aligns best with the "on-device" goal.
    *   **Option B (Local Backend):** Use the existing Python Flask server (`server.py`) running locally on the device (requires Python environment on mobile - challenging) or on the same local network. The PWA would communicate with this local server.
    *   **Option C (Cloud Backend):** Interact directly with Cartesia's cloud API (requires API key management on the client - insecure) or use the existing Flask server as a proxy deployed to the cloud (more secure).
*   **External APIs:** Standard `fetch` API or libraries like `axios` for calling weather APIs (e.g., OpenWeatherMap, WeatherAPI).

## 4. Architecture Overview (Assuming Option C initially for simplicity)

1.  **Frontend (PWA):**
    *   Handles UI rendering, user input.
    *   Manages PWA lifecycle (service worker, manifest).
    *   Sends user requests to the Backend API.
    *   Displays results received from the backend.
2.  **Backend API (e.g., Existing Flask App deployed):**
    *   Receives requests from the PWA.
    *   Uses Cartesia SSM (via `model_loader.py` or direct Cartesia API call) to interpret the user's request (intent recognition, entity extraction).
    *   If the task requires external data (like weather):
        *   Calls the relevant external API (e.g., Weather API) using necessary parameters extracted by the SSM.
        *   Formats the external API response.
    *   Sends the final result back to the PWA.
3.  **Cartesia SSM:**
    *   Interprets natural language requests.
    *   Provides structured output (intent, entities).
4.  **External Services:**
    *   Weather API, etc.

## 5. Development Workflow

1.  **Setup:**
    *   Initialize a new frontend project (e.g., `npx create-react-app cartesia-mobile-app` or similar for Vue/Svelte).
    *   Set up PWA basics (`manifest.json`, service worker placeholder).
2.  **Frontend UI:**
    *   Create components for input (text field), output display area, and potentially an "Install App" button.
    *   Implement basic state management for input and output.
3.  **API Interaction:**
    *   Define functions to send user input to the backend API endpoint.
    *   Handle API responses (success and error states).
    *   Display results in the UI.
4.  **Backend Adaptation (If using Flask):**
    *   Create a new API endpoint (e.g., `/api/process-request`) in `server.py`.
    *   This endpoint should take user text, use the SSM to parse it (similar to `test_framework.py` logic perhaps).
    *   Implement task-specific logic (e.g., if intent is "get_weather", call weather API).
    *   Ensure CORS is configured correctly for the PWA domain.
    *   Deploy the Flask app (e.g., using Docker, Heroku, PythonAnywhere).
5.  **SSM Task Logic:**
    *   Define the prompts or methods for interacting with the SSM to reliably extract intent and entities for target tasks (start with weather).
6.  **Weather API Integration:**
    *   Sign up for a weather API key.
    *   Add logic in the backend to call the weather API using the location extracted by the SSM.
    *   Securely manage the weather API key (use environment variables on the backend).
7.  **PWA Enhancement:**
    *   Implement a robust service worker using Workbox for caching app shell and potentially API responses.
    *   Refine `manifest.json` (icons, theme colors, etc.).
    *   Test installability and offline behavior.
8.  **Testing:**
    *   Unit tests for frontend components and utility functions.
    *   Integration tests for API interactions.
    *   End-to-end tests simulating user flows.
    *   PWA audits (Lighthouse).
9.  **Deployment:**
    *   Deploy the frontend PWA (e.g., Netlify, Vercel, GitHub Pages).
    *   Ensure the deployed backend API is accessible.

## 6. Key Considerations & Challenges

*   **SSM On-Device Feasibility:** This is the biggest unknown. Running complex models like SSMs directly in a browser environment is challenging due to performance, memory constraints, and model availability in a suitable format (JS/WASM). Thorough investigation with Cartesia's resources is needed.
*   **API Key Security:** If interacting directly with cloud APIs (Cartesia, Weather) from the frontend, API keys can be exposed. A backend proxy is the standard secure approach.
*   **Performance:** On-device SSM execution (if possible) or network latency to the backend API will significantly impact user experience.
*   **Offline Functionality:** Define what should work offline. The app shell is standard PWA; offline task execution requires on-device SSM and potentially cached data.
*   **Task Scope:** Start with one simple task (weather) and expand gradually. Defining the interaction patterns and expected SSM outputs for each task is crucial.
*   **Error Handling:** Robust handling for API errors, SSM interpretation failures, network issues.

## 7. Next Steps (Immediate)

1.  **Investigate Cartesia's capabilities for browser/on-device execution:** Check their documentation, SDKs, or contact their support.
2.  **Choose Frontend Stack:** Decide on React/Vue/Svelte.
3.  **Set up Frontend Project:** Initialize the codebase.
4.  **Set up Backend:** Decide on deployment strategy for the Flask app or alternative backend.
5.  **Obtain API Keys:** Get keys for Cartesia (if needed for cloud) and a weather service.