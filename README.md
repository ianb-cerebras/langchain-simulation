# User Research Simulation Platform

An AI-powered web application that simulates user research studies using Next.js and the Cerebras AI API. Generate realistic personas, conduct simulated interviews, and synthesize insights for product research.

## Features

- **AI-Powered Research**: Uses Cerebras AI to generate diverse user personas and simulate realistic interviews
- **Interactive Dashboard**: View key insights, observations, and takeaways from research simulations
- **Participant Management**: Browse simulated participants with detailed demographics and personality traits
- **Modern UI**: Built with Next.js, TypeScript, and Shadcn UI components with dark mode support
- **Real-time Results**: Dynamic dashboard that updates with simulation results

## Getting Started

### Prerequisites

- Node.js 18+ 
- Python 3.8+
- Cerebras API key (optional - app works with fallback data)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simulation-webapp
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Install Python dependencies:
```bash
python3 -m pip install -r requirements.txt
```

4. Set up environment variables (optional):
```bash
# Create .env.local file
CEREBRAS_API_KEY=your_cerebras_api_key
```

### Running the Application

1. Start the development server:
```bash
npm run dev
```

2. Open [http://localhost:3000](http://localhost:3000) in your browser

3. Navigate to `/config` to start a simulation

## Usage

### Running a Simulation

1. **Configure Research**: Go to `/config` and enter:
   - Research question (e.g., "How would users feel about a pink iPhone?")
   - Target audience (e.g., "Gen Z")
   - Number of interviews (1-50)

2. **Run Simulation**: Click "Run Simulation" to start the AI-powered research

3. **View Results**: Automatically redirected to `/dashboard` to see:
   - Key insights and observations
   - Simulated participant data
   - Interactive charts and visualizations

### Dashboard Features

- **Section Cards**: Display key insights, observations, and takeaways
- **Participant Table**: Browse simulated participants with clickable rows for detailed information
- **Interactive Charts**: Visualize research data and trends
- **Dark Mode**: Toggle between light and dark themes

## Technical Architecture

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Components**: Shadcn UI with Radix UI primitives
- **Styling**: Tailwind CSS
- **State Management**: React hooks (useState, useEffect)

### Backend
- **API Routes**: Next.js API routes for serverless functions
- **Python Integration**: Child process spawning for AI script execution
- **Data Storage**: Local JSON files for configuration and results

### AI Engine
- **Language Model**: Cerebras AI API (llama3.1-8b)
- **Script**: Python-based research simulation engine
- **Features**: Persona generation, interview simulation, insight synthesis

## File Structure

```
simulation-webapp/
├── app/
│   ├── api/
│   │   ├── run-uxr/route.ts    # Execute Python simulation
│   │   └── uxr-result/route.ts # Serve simulation results
│   ├── config/page.tsx          # Configuration interface
│   ├── dashboard/page.tsx       # Results dashboard
│   └── layout.tsx               # Root layout with theme provider
├── components/
│   ├── data-table.tsx           # Interactive participant table
│   ├── section-cards.tsx        # Insight display cards
│   └── theme-toggle.tsx         # Dark mode toggle
├── enhanced_uxr.py              # Main AI research engine
├── requirements.txt              # Python dependencies
└── package.json                 # Node.js dependencies
```

## API Endpoints

- `POST /api/run-uxr`: Execute research simulation
- `GET /api/uxr-result`: Retrieve latest simulation results

## Configuration

The application can run with or without a Cerebras API key:

- **With API Key**: Full AI-powered simulations with realistic personas and responses
- **Without API Key**: Uses fallback data for demonstration purposes

## Development

### Adding New Features

1. **UI Components**: Add new Shadcn UI components in `components/`
2. **API Routes**: Create new routes in `app/api/`
3. **Python Logic**: Extend `enhanced_uxr.py` for additional research capabilities

### Customizing the AI Engine

The Python script (`enhanced_uxr.py`) can be modified to:
- Add new persona generation strategies
- Implement different interview question types
- Enhance insight synthesis algorithms

## Deployment

This is a Next.js application that can be deployed to Vercel


Built with Next.js, TypeScript, and Cerebras AI
