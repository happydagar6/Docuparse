const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateCitation(paperId, format = "apa"){
    const res = await fetch(`${API_URL}/api/citations/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId, format }),
    });
    if(!res.ok) throw new Error(`Error generating citation: ${res.statusText}`);
    return res.json();
}

export async function batchCitations(paperIds = [], format = "apa"){
    const res = await fetch(`${API_URL}/api/citations/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: paperIds, format }),
    });
    if(!res.ok) throw new Error(`Error generating batch citations: ${res.statusText}`);
    return res.json();
}

export async function getCitationFormats(){
    const res = await fetch(`${API_URL}/api/citations/formats`);
    if(!res.ok) throw new Error(`Error fetching citation formats: ${res.statusText}`);
    return res.json();
}

export async function exportBibtex(paperIds){
    const res = await fetch(`${API_URL}/api/citations/export/bibtex`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: paperIds }),
    });
    if(!res.ok) throw new Error(`Error exporting BibTeX: ${res.statusText}`);
    return res.text();
};

