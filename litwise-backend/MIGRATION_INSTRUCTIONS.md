# Database Migration Instructions

## Add file_type Column to Support Multi-Format Uploads

### Option 1: Run via Supabase SQL Editor (Recommended)

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Navigate to: **SQL Editor**
3. Click **New Query**
4. Copy and paste the SQL below:

```sql
-- Add file_type column to papers table
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS file_type VARCHAR(10) DEFAULT 'pdf';

-- Add comment for documentation
COMMENT ON COLUMN papers.file_type IS 'File extension without dot (pdf, txt, csv, md, docx)';

-- Create index for file type queries
CREATE INDEX IF NOT EXISTS idx_papers_file_type ON papers(file_type);

-- Update existing records to have 'pdf' as file_type
UPDATE papers
SET file_type = 'pdf'
WHERE file_type IS NULL;
```

5. Click **Run** (or press Ctrl+Enter)
6. Verify the output shows "Success"

### Option 2: Use psql Command Line

If you have direct PostgreSQL access:

```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-HOST]:5432/postgres" -f migrations/add_file_type_column.sql
```

### Verification

After running the migration, verify it worked:

```sql
-- Check if column exists
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'papers' AND column_name = 'file_type';

-- Check existing data
SELECT file_type, COUNT(*) 
FROM papers 
GROUP BY file_type;
```

You should see:
- Column `file_type` exists with type `character varying(10)`
- Default value is `'pdf'::character varying`
- All existing papers have `file_type = 'pdf'`

### What This Enables

After this migration, your system will support:
- ✅ PDF files (.pdf)
- ✅ Text files (.txt, .md, .markdown)
- ✅ CSV files (.csv, .tsv)
- ✅ Future formats (easy to add)

Each uploaded document will have its file type tracked in the database.
