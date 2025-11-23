import Database from 'better-sqlite3';
import path from 'path';

// Connect to the SQLite database from the parent directory
const dbPath = path.join(process.cwd(), '..', 'jobs.db');
const db = new Database(dbPath, { readonly: true });

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  url: string;
  posted_date: string;
  board_source: string;
  salary_min?: number | string;
  salary_max?: number | string;
  job_type?: string;
  remote_type?: string;
  scraped_at?: string;
  enriched_at?: string;
  company_id?: string;
  company_size?: string;
  industry?: string;
  headquarters_location?: string;
  taiwan_team_count?: number;
  ranking_score?: number;
  company_website?: string;
}

export interface Company {
  id: string;
  name: string;
  linkedin_url?: string;
  website?: string;
  industry?: string;
  company_size?: string;
  headquarters_location?: string;
  description?: string;
  total_employees?: number;
  taiwan_employee_count?: number;
  enriched_at?: string;
  source?: string;
}

export interface TeamMember {
  id: number;
  company_id: string;
  name: string;
  title?: string;
  location?: string;
  city?: string;
  country?: string;
  linkedin_url?: string;
}

// Get all jobs ordered by rank (desc)
export function getJobs(limit: number = 100, minTaiwanTeam: number = 0): Job[] {
  const stmt = db.prepare(`
    SELECT * FROM jobs
    WHERE taiwan_team_count >= ?
    ORDER BY ranking_score DESC NULLS LAST, posted_date DESC
    LIMIT ?
  `);
  return stmt.all(minTaiwanTeam, limit) as Job[];
}

// Search jobs by keyword
export function searchJobs(query: string, limit: number = 100): Job[] {
  const searchTerm = `%${query}%`;
  const stmt = db.prepare(`
    SELECT * FROM jobs
    WHERE title LIKE ? OR company LIKE ? OR description LIKE ?
    ORDER BY ranking_score DESC NULLS LAST, posted_date DESC
    LIMIT ?
  `);
  return stmt.all(searchTerm, searchTerm, searchTerm, limit) as Job[];
}

// Get a single job by ID
export function getJobById(id: string): Job | undefined {
  const stmt = db.prepare('SELECT * FROM jobs WHERE id = ?');
  return stmt.get(id) as Job | undefined;
}

// Get all companies
export function getCompanies(limit: number = 100): Company[] {
  const stmt = db.prepare(`
    SELECT * FROM companies
    ORDER BY taiwan_employee_count DESC NULLS LAST
    LIMIT ?
  `);
  return stmt.all(limit) as Company[];
}

// Get a single company by ID
export function getCompanyById(id: string): Company | undefined {
  const stmt = db.prepare('SELECT * FROM companies WHERE id = ?');
  return stmt.get(id) as Company | undefined;
}

// Get jobs for a specific company
export function getJobsByCompany(companyId: string): Job[] {
  const stmt = db.prepare(`
    SELECT * FROM jobs
    WHERE company_id = ?
    ORDER BY ranking_score DESC NULLS LAST, posted_date DESC
  `);
  return stmt.all(companyId) as Job[];
}

// Get all team members for a company
export function getTeamMembersByCompany(companyId: string): TeamMember[] {
  const stmt = db.prepare(`
    SELECT * FROM team_members
    WHERE company_id = ?
    ORDER BY country, city, name
  `);
  return stmt.all(companyId) as TeamMember[];
}

// Get team members filtered by country
export function getTeamMembersByCountry(companyId: string, country: string): TeamMember[] {
  const stmt = db.prepare(`
    SELECT * FROM team_members
    WHERE company_id = ? AND country = ?
    ORDER BY city, name
  `);
  return stmt.all(companyId, country) as TeamMember[];
}

// Get all unique countries for a company's team members
export function getCountriesByCompany(companyId: string): string[] {
  const stmt = db.prepare(`
    SELECT DISTINCT country FROM team_members
    WHERE company_id = ? AND country IS NOT NULL
    ORDER BY country
  `);
  const result = stmt.all(companyId) as { country: string }[];
  return result.map(r => r.country);
}

// Get a single team member by ID
export function getTeamMemberById(id: number): TeamMember | undefined {
  const stmt = db.prepare('SELECT * FROM team_members WHERE id = ?');
  return stmt.get(id) as TeamMember | undefined;
}

export default db;
