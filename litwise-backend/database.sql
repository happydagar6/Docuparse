create table public.users (
  id uuid not null default extensions.uuid_generate_v4 (),
  email text not null,
  created_at timestamp with time zone not null default timezone ('utc'::text, now()),
  updated_at timestamp with time zone not null default timezone ('utc'::text, now()),
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email)
) TABLESPACE pg_default;

create trigger update_users_updated_at BEFORE
update on users for EACH row
execute FUNCTION update_updated_at_column ();




create table public.synthesis_history (
  id uuid not null default gen_random_uuid (),
  query text not null,
  paper_count integer not null default 0,
  max_papers integer not null default 20,
  themes jsonb null default '[]'::jsonb,
  key_findings jsonb null default '[]'::jsonb,
  research_gaps jsonb null default '[]'::jsonb,
  trends jsonb null default '{}'::jsonb,
  top_papers jsonb null default '[]'::jsonb,
  paper_ids text[] null default array[]::text[],
  search_results jsonb null default '[]'::jsonb,
  user_id text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  tags text[] null default array[]::text[],
  constraint synthesis_history_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_query on public.synthesis_history using gin (to_tsvector('english'::regconfig, query)) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_created_at on public.synthesis_history using btree (created_at desc) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_user_id on public.synthesis_history using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_tags on public.synthesis_history using gin (tags) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_themes on public.synthesis_history using gin (themes) TABLESPACE pg_default;

create index IF not exists idx_synthesis_history_paper_ids on public.synthesis_history using gin (paper_ids) TABLESPACE pg_default;

create trigger trigger_update_synthesis_history_updated_at BEFORE
update on synthesis_history for EACH row
execute FUNCTION update_synthesis_history_updated_at ();



create view public.synthesis_stats as
select
  date_trunc('day'::text, created_at) as date,
  count(*) as total_syntheses,
  avg(paper_count) as avg_papers_per_synthesis,
  count(distinct query) as unique_queries
from
  synthesis_history
group by
  (date_trunc('day'::text, created_at))
order by
  (date_trunc('day'::text, created_at)) desc;



create table public.study_plans (
  id uuid not null default gen_random_uuid (),
  paper_id uuid null,
  paper_title text not null,
  duration_weeks integer not null,
  exam_type text not null,
  study_style text not null,
  plan_data jsonb not null,
  created_at timestamp with time zone null default now(),
  constraint study_plans_pkey primary key (id),
  constraint study_plans_paper_id_fkey foreign KEY (paper_id) references papers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_study_plans_paper_id on public.study_plans using btree (paper_id) TABLESPACE pg_default;

create index IF not exists idx_study_plans_created_at on public.study_plans using btree (created_at desc) TABLESPACE pg_default;




--- Papers Table ----

create table public.papers (
  id uuid not null default extensions.uuid_generate_v4 (),
  user_id uuid null,
  title text not null,
  summary jsonb null,
  content_text text null,
  embedding_id text null,
  created_at timestamp with time zone not null default timezone ('utc'::text, now()),
  updated_at timestamp with time zone not null default timezone ('utc'::text, now()),
  processing_status text null default 'uploaded'::text,
  ai_generated_at timestamp with time zone null,
  processing_error text null,
  page_info jsonb null,
  file_size integer null default 0,
  filename text null,
  authors jsonb null default '[]'::jsonb,
  publication_year integer null,
  doi text null,
  keywords text[] null default array[]::text[],
  journal_or_conference text null,
  abstract text null,
  has_images boolean null default false,
  has_tables boolean null default false,
  has_equations boolean null default false,
  constraint papers_pkey primary key (id),
  constraint papers_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE,
  constraint check_processing_status check (
    (
      processing_status = any (
        array[
          'uploaded'::text,
          'processing'::text,
          'completed'::text,
          'failed'::text
        ]
      )
    )
  ),
  constraint papers_processing_status_check check (
    (
      processing_status = any (
        array[
          'uploaded'::text,
          'processing'::text,
          'completed'::text,
          'failed'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_papers_user_id on public.papers using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_papers_title on public.papers using gin (to_tsvector('english'::regconfig, title)) TABLESPACE pg_default;

create index IF not exists idx_papers_summary on public.papers using gin (summary) TABLESPACE pg_default;

create index IF not exists idx_papers_processing_status on public.papers using btree (processing_status) TABLESPACE pg_default;

create index IF not exists idx_papers_page_info on public.papers using gin (page_info) TABLESPACE pg_default;

create index IF not exists idx_papers_authors on public.papers using gin (authors) TABLESPACE pg_default;

create index IF not exists idx_papers_publication_year on public.papers using btree (publication_year) TABLESPACE pg_default;

create index IF not exists idx_papers_doi on public.papers using btree (doi) TABLESPACE pg_default;

create index IF not exists idx_papers_keywords on public.papers using gin (keywords) TABLESPACE pg_default;

create index IF not exists idx_papers_abstract on public.papers using gin (to_tsvector('english'::regconfig, abstract)) TABLESPACE pg_default;

create index IF not exists idx_papers_has_images on public.papers using btree (has_images) TABLESPACE pg_default
where
  (has_images = true);

create index IF not exists idx_papers_has_tables on public.papers using btree (has_tables) TABLESPACE pg_default
where
  (has_tables = true);

create index IF not exists idx_papers_has_equations on public.papers using btree (has_equations) TABLESPACE pg_default
where
  (has_equations = true);

create trigger update_papers_updated_at BEFORE
update on papers for EACH row
execute FUNCTION update_updated_at_column ();




--- Paper Citations Table ----

create table public.paper_citations (
  id uuid not null default extensions.uuid_generate_v4 (),
  paper_id uuid not null,
  citation_text text not null,
  in_text_refs text[] null,
  title text null,
  authors jsonb null default '[]'::jsonb,
  year integer null,
  doi text null,
  venue text null,
  relevance_summary text null,
  citation_context text[] null,
  mention_count integer null default 1,
  importance_score double precision null default 0.0,
  extraction_method text null default 'auto'::text,
  citation_type text null,
  verified boolean null default false,
  created_at timestamp with time zone not null default timezone ('utc'::text, now()),
  updated_at timestamp with time zone not null default timezone ('utc'::text, now()),
  constraint paper_citations_pkey primary key (id),
  constraint paper_citations_paper_id_citation_text_key unique (paper_id, citation_text),
  constraint paper_citations_paper_id_fkey foreign KEY (paper_id) references papers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_paper_citations_paper_id on public.paper_citations using btree (paper_id) TABLESPACE pg_default;

create index IF not exists idx_paper_citations_doi on public.paper_citations using btree (doi) TABLESPACE pg_default
where
  (doi is not null);

create index IF not exists idx_paper_citations_title on public.paper_citations using gin (to_tsvector('english'::regconfig, title)) TABLESPACE pg_default;

create index IF not exists idx_paper_citations_authors on public.paper_citations using gin (authors) TABLESPACE pg_default;

create index IF not exists idx_paper_citations_importance on public.paper_citations using btree (importance_score desc) TABLESPACE pg_default;

create trigger update_paper_citations_updated_at BEFORE
update on paper_citations for EACH row
execute FUNCTION update_updated_at_column ();





--- Literature Review ---

create table public.literature_reviews (
  id uuid not null default gen_random_uuid (),
  topic text not null,
  review_style text not null,
  paper_ids text[] not null,
  paper_count integer not null default 0,
  content jsonb not null,
  word_count integer null default 0,
  user_id text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  constraint literature_reviews_pkey primary key (id),
  constraint literature_reviews_review_style_check check (
    (
      review_style = any (
        array[
          'narrative'::text,
          'systematic'::text,
          'critical'::text
        ]
      )
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_literature_reviews_topic on public.literature_reviews using gin (to_tsvector('english'::regconfig, topic)) TABLESPACE pg_default;

create index IF not exists idx_literature_reviews_created_at on public.literature_reviews using btree (created_at desc) TABLESPACE pg_default;

create index IF not exists idx_literature_reviews_paper_ids on public.literature_reviews using gin (paper_ids) TABLESPACE pg_default;

create trigger trigger_update_literature_reviews_updated_at BEFORE
update on literature_reviews for EACH row
execute FUNCTION update_literature_reviews_updated_at ();




--- Citations Relationships ---

create table public.citation_relationships (
  id uuid not null default extensions.uuid_generate_v4 (),
  citing_paper_id uuid not null,
  cited_paper_id uuid null,
  citation_id uuid not null,
  relationship_type text null default 'cites'::text,
  confidence_score double precision null default 1.0,
  created_at timestamp with time zone not null default timezone ('utc'::text, now()),
  constraint citation_relationships_pkey primary key (id),
  constraint citation_relationships_citing_paper_id_citation_id_key unique (citing_paper_id, citation_id),
  constraint citation_relationships_citation_id_fkey foreign KEY (citation_id) references paper_citations (id) on delete CASCADE,
  constraint citation_relationships_cited_paper_id_fkey foreign KEY (cited_paper_id) references papers (id) on delete set null,
  constraint citation_relationships_citing_paper_id_fkey foreign KEY (citing_paper_id) references papers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_citation_relationships_citing on public.citation_relationships using btree (citing_paper_id) TABLESPACE pg_default;

create index IF not exists idx_citation_relationships_cited on public.citation_relationships using btree (cited_paper_id) TABLESPACE pg_default;



--- Chat Session ---
create table public.chat_sessions (
  id uuid not null default gen_random_uuid (),
  paper_id uuid null,
  title text null,
  created_at timestamp with time zone null default now(),
  updated_at timestamp with time zone null default now(),
  user_id uuid null,
  constraint chat_sessions_pkey primary key (id),
  constraint chat_sessions_paper_id_fkey foreign KEY (paper_id) references papers (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_chat_sessions_paper_id on public.chat_sessions using btree (paper_id) TABLESPACE pg_default;




--- Chat Messages ---

create table public.chat_messages (
  id uuid not null default gen_random_uuid (),
  session_id uuid null,
  role text not null,
  content text not null,
  sources jsonb null default '[]'::jsonb,
  created_at timestamp with time zone null default now(),
  constraint chat_messages_pkey primary key (id),
  constraint chat_messages_session_id_fkey foreign KEY (session_id) references chat_sessions (id) on delete CASCADE,
  constraint chat_messages_role_check check (
    (
      role = any (array['user'::text, 'assistant'::text])
    )
  )
) TABLESPACE pg_default;

create index IF not exists idx_chat_messages_session_id on public.chat_messages using btree (session_id) TABLESPACE pg_default;

create index IF not exists idx_chat_messages_created_at on public.chat_messages using btree (created_at) TABLESPACE pg_default;



--- Chat Memory ---

create table public.chat_memory (
  id uuid not null default gen_random_uuid (),
  session_id uuid null,
  memory_data jsonb null default '{}'::jsonb,
  updated_at timestamp with time zone null default now(),
  constraint chat_memory_pkey primary key (id),
  constraint chat_memory_session_id_key unique (session_id),
  constraint chat_memory_session_id_fkey foreign KEY (session_id) references chat_sessions (id) on delete CASCADE
) TABLESPACE pg_default;

create index IF not exists idx_chat_memory_session_id on public.chat_memory using btree (session_id) TABLESPACE pg_default;





--- Notes Table ---
-- Table for user notes/reminders for research and study purposes

create table public.notes (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  title text not null,
  content text not null default ''::text,
  color text null default '#fef3c7'::text,
  pinned boolean not null default false,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint notes_pkey primary key (id),
  constraint notes_user_id_fkey foreign key (user_id) references auth.users (id) on delete cascade
) TABLESPACE pg_default;

-- Indexes for notes table
create index IF not exists idx_notes_user_id on public.notes using btree (user_id) TABLESPACE pg_default;

create index IF not exists idx_notes_created_at on public.notes using btree (created_at desc) TABLESPACE pg_default;

create index IF not exists idx_notes_pinned on public.notes using btree (pinned, created_at desc) TABLESPACE pg_default;

-- Trigger to update updated_at timestamp
create trigger trigger_update_notes_updated_at BEFORE
update on notes for EACH row
execute FUNCTION update_updated_at_column ();








-- ============================================
-- QUIZ GENERATOR FEATURE - DATABASE SCHEMA
-- ============================================

-- 1. Main quizzes table
CREATE TABLE IF NOT EXISTS quizzes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  
  -- Quiz configuration
  difficulty_level TEXT NOT NULL CHECK (difficulty_level IN ('easy', 'medium', 'hard')),
  topic TEXT NOT NULL,
  question_count INT NOT NULL CHECK (question_count > 0 AND question_count <= 100),
  quiz_type TEXT NOT NULL CHECK (quiz_type IN ('fact-based', 'scenario-based', 'mixed')),
  
  -- Content storage
  questions JSONB NOT NULL DEFAULT '[]'::jsonb, 
  retrieval_context JSONB NOT NULL DEFAULT '[]'::jsonb, 
  
  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints (Unique constraints ARE allowed inside CREATE TABLE)
  CONSTRAINT user_paper_quiz_check UNIQUE(user_id, paper_id, title)
);

-- 2. Create Indexes for 'quizzes' separately
CREATE INDEX IF NOT EXISTS idx_quizzes_user_id ON quizzes(user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_paper_id ON quizzes(paper_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_created_at ON quizzes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quizzes_difficulty ON quizzes(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_quizzes_type ON quizzes(quiz_type);


-- 3. Quiz attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  
  -- Attempt data
  responses JSONB NOT NULL DEFAULT '{}'::jsonb, 
  score INT CHECK (score >= 0 AND score <= 100),
  correct_answers INT DEFAULT 0,
  total_questions INT NOT NULL,
  time_spent_seconds INT,
  
  -- Metadata
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- 4. Create Indexes for 'quiz_attempts' separately
CREATE INDEX IF NOT EXISTS idx_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_quiz_id ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_attempts_completed_at ON quiz_attempts(completed_at DESC);


-- 5. Quiz feedback/notes table
CREATE TABLE IF NOT EXISTS quiz_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  attempt_id UUID NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
  question_index INT NOT NULL,
  user_feedback TEXT,
  
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- 6. Update timestamp trigger
CREATE OR REPLACE FUNCTION update_quizzes_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists to prevent errors on re-runs
DROP TRIGGER IF EXISTS quizzes_timestamp_trigger ON quizzes;

CREATE TRIGGER quizzes_timestamp_trigger
BEFORE UPDATE ON quizzes
FOR EACH ROW
EXECUTE FUNCTION update_quizzes_timestamp();


-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS
ALTER TABLE quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_feedback ENABLE ROW LEVEL SECURITY;

-- Quizzes RLS Policies
CREATE POLICY "Users can view their own quizzes"
  ON quizzes FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create quizzes for their papers"
  ON quizzes FOR INSERT
  WITH CHECK (
    auth.uid() = user_id AND
    EXISTS (
      SELECT 1 FROM papers 
      WHERE papers.id = quizzes.paper_id 
      AND papers.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own quizzes"
  ON quizzes FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own quizzes"
  ON quizzes FOR DELETE
  USING (auth.uid() = user_id);

-- Quiz Attempts RLS Policies
CREATE POLICY "Users can view their own attempts"
  ON quiz_attempts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create attempts for their quizzes"
  ON quiz_attempts FOR INSERT
  WITH CHECK (
    auth.uid() = user_id AND
    EXISTS (
      SELECT 1 FROM quizzes 
      WHERE quizzes.id = quiz_attempts.quiz_id 
      AND quizzes.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update their own attempts"
  ON quiz_attempts FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Quiz Feedback RLS Policies
CREATE POLICY "Users can view feedback for their attempts"
  ON quiz_feedback FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM quiz_attempts 
      WHERE quiz_attempts.id = quiz_feedback.attempt_id 
      AND quiz_attempts.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create feedback for their attempts"
  ON quiz_feedback FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM quiz_attempts 
      WHERE quiz_attempts.id = quiz_feedback.attempt_id 
      AND quiz_attempts.user_id = auth.uid()
    )
  );