"""SQLAlchemy database models"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class JobBoardEnum(enum.Enum):
    """Job board enumeration"""
    INDEED = "indeed"
    LINKEDIN = "linkedin"
    REMOTEOK = "remoteok"
    WEWORKREMOTELY = "weworkremotely"


class Job(Base):
    """Job listing table"""
    __tablename__ = 'jobs'

    id = Column(String(16), primary_key=True)
    title = Column(String(500), nullable=False)
    company = Column(String(200), nullable=False)
    location = Column(String(200))
    description = Column(Text)
    url = Column(String(1000), nullable=False)
    posted_date = Column(DateTime)
    board_source = Column(SQLEnum(JobBoardEnum), nullable=False)

    salary_min = Column(Float)
    salary_max = Column(String(50))
    job_type = Column(String(50))
    remote_type = Column(String(50))

    scraped_at = Column(DateTime, default=datetime.now)

    # Enrichment fields
    company_id = Column(String(100), ForeignKey('companies.id'))
    company_size = Column(String(50))
    industry = Column(String(100))
    headquarters_location = Column(String(200))
    taiwan_team_count = Column(Integer, default=0)
    enriched_at = Column(DateTime)
    ranking_score = Column(Float, default=0.0)

    # Relationships
    company_profile = relationship("Company", back_populates="jobs")

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"


class Company(Base):
    """Company profile table"""
    __tablename__ = 'companies'

    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    linkedin_url = Column(String(500))
    website = Column(String(500))
    industry = Column(String(100))
    company_size = Column(String(50))
    headquarters_location = Column(String(200))
    description = Column(Text)

    total_employees = Column(Integer)
    taiwan_employee_count = Column(Integer, default=0)

    enriched_at = Column(DateTime)
    source = Column(String(50))  # peopledatalabs, coresignal

    # Relationships
    jobs = relationship("Job", back_populates="company_profile")
    team_members = relationship("TeamMember", back_populates="company")

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', taiwan_count={self.taiwan_employee_count})>"


class TeamMember(Base):
    """Team member table (Taiwan employees)"""
    __tablename__ = 'team_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(String(100), ForeignKey('companies.id'), nullable=False)
    name = Column(String(200))
    title = Column(String(200))
    location = Column(String(200))
    city = Column(String(100))
    country = Column(String(100))
    linkedin_url = Column(String(500))

    # Relationships
    company = relationship("Company", back_populates="team_members")

    def __repr__(self):
        return f"<TeamMember(name='{self.name}', title='{self.title}', location='{self.location}')>"
