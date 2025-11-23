# JobQuest Frontend

A distinctive Next.js frontend for the Job Search Assistant with Tailwind CSS v4.

## Features

- 🎯 **Job Listings**: Browse jobs ranked by relevance and Asia team presence
- 🔍 **Search**: Search jobs by title, company, or description
- 🏢 **Company Profiles**: View detailed company information with LinkedIn links
- 👥 **Employee Directory**: Explore team members by location with country filtering
- 👤 **Employee Profiles**: View individual employee profiles with LinkedIn links
- ✨ **Creative Design**: Aurora Borealis-inspired color palette with unique fonts and animations

## Design Features

### Typography
- **Display Font**: Orbitron (futuristic, bold headers)
- **Body Font**: Space Mono (modern monospace)
- **Accent Font**: JetBrains Mono (code and technical elements)

### Color Palette (Aurora Borealis Theme)
- **Background**: Deep space gradients (void, deep, midnight)
- **Accents**: Aurora teal, green, purple, pink
- **Highlights**: Shimmer gold and frost

### Animations
- Fade-in page loads
- Slide-up content reveals
- Staggered animations for lists
- Card glow effects on hover
- Shimmer effects for loading states

## Prerequisites

- Node.js 18+ or Yarn
- SQLite database (`jobs.db`) in the parent directory

## Installation

```bash
# Install dependencies
yarn install
# or
npm install
```

## Running the Development Server

```bash
# Start the dev server
yarn dev
# or
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Building for Production

```bash
# Build the application
yarn build
# or
npm run build

# Start the production server
yarn start
# or
npm start
```

## Project Structure

```
frontend/
├── app/                      # Next.js app directory
│   ├── api/                  # API routes
│   │   ├── jobs/            # Jobs API endpoints
│   │   ├── companies/       # Companies API endpoints
│   │   └── employees/       # Employees API endpoints
│   ├── companies/           # Company pages
│   │   ├── page.tsx         # Companies list
│   │   └── [id]/            # Company detail & employees
│   ├── employees/           # Employee pages
│   │   └── [id]/            # Employee profile
│   ├── jobs/                # Job pages
│   │   └── [id]/            # Job detail
│   ├── globals.css          # Global styles & Tailwind config
│   ├── layout.tsx           # Root layout
│   └── page.tsx             # Home page (jobs list)
├── components/              # Reusable components
│   ├── Header.tsx           # Navigation header
│   ├── JobCard.tsx          # Job listing card
│   └── SearchBar.tsx        # Search input
├── lib/                     # Utilities
│   └── db.ts                # Database connection & queries
├── public/                  # Static assets
├── next.config.js           # Next.js configuration
├── postcss.config.mjs       # PostCSS configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
```

## Pages

### Jobs (`/`)
- Lists all jobs ordered by ranking score
- Search functionality
- Filter by minimum Asia team members
- Click job to view details
- Click company to view company profile

### Job Detail (`/jobs/[id]`)
- Full job description
- Company information
- Apply button linking to original job board
- Related company profile link

### Companies (`/companies`)
- Grid of all companies
- Shows company size, industry, and Asia team count
- Click to view company details

### Company Detail (`/companies/[id]`)
- Company overview and description
- LinkedIn and website links
- Open positions at the company
- Team members preview (first 12)
- Country filter for team members
- Link to full employees list

### Employees List (`/companies/[id]/employees`)
- Full list of team members
- Filter by country
- Grouped by country when viewing all
- Click to view employee profile

### Employee Profile (`/employees/[id]`)
- Employee name and title
- Location information
- LinkedIn profile link
- Company information
- Back to team link

## Database Connection

The frontend connects to the SQLite database (`jobs.db`) in the parent directory using `better-sqlite3`. The database is accessed in read-only mode.

### Required Tables
- `jobs`: Job listings with enrichment data
- `companies`: Company profiles
- `team_members`: Employee information

## API Routes

- `GET /api/jobs` - Get all jobs (supports `?q=search&limit=100&minTaiwanTeam=0`)
- `GET /api/jobs/[id]` - Get job by ID
- `GET /api/companies` - Get all companies (supports `?limit=100`)
- `GET /api/companies/[id]` - Get company with jobs and team members
- `GET /api/employees/[id]` - Get employee by ID

## Styling

The app uses Tailwind CSS v4 with custom theme variables defined in `globals.css`. The design avoids generic "AI slop" aesthetics with:

- Unique font combinations (Orbitron, Space Mono, JetBrains Mono)
- Creative Aurora Borealis color palette
- Layered backgrounds with gradients
- Glow effects and animations
- Consistent CSS variables for theming

## Environment Variables

No environment variables needed - the app reads directly from the SQLite database.

## Troubleshooting

### Database not found
Ensure `jobs.db` exists in the parent directory (`../jobs.db` relative to frontend).

### Build errors
Run `yarn install` or `npm install` to ensure all dependencies are installed.

### Styling issues
Clear `.next` cache and rebuild:
```bash
rm -rf .next
yarn dev
```

## License

Same as parent project
