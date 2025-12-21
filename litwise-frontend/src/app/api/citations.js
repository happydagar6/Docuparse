import { apiRequest } from '@/lib/api';

export async function generateCitation(paperId, format = "apa"){
    return apiRequest('/api/citations/generate', {
        method: 'POST',
        body: JSON.stringify({ paper_id: paperId, format }),
    });
}

export async function batchCitations(paperIds = [], format = "apa"){
    return apiRequest('/api/citations/batch', {
        method: 'POST',
        body: JSON.stringify({ paper_ids: paperIds, format }),
    });
}

export async function getCitationFormats(){
    return apiRequest('/api/citations/formats');
}

export async function exportBibtex(paperIds){
    const response = await apiRequest('/api/citations/export/bibtex', {
        method: 'POST',
        body: JSON.stringify({ paper_ids: paperIds }),
    });
    // For text responses, we need to handle it differently
    return response.text ? await response.text() : response;
}

