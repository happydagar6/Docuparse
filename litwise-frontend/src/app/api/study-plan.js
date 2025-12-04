const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateStudyPlan(data) {
    const res = await fetch (`${API_URL}/api/study-plan/generate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    if(!res.ok) throw new Error('Failed to generate study plan');
    return res.json();
};

export async function getStudyPlans(paperId = null){
    const url = paperId
    ? `${API_URL}/api/study-plan/list?paper_id=${paperId}`
    : `${API_URL}/api/study-plan/list`;

    const res = await fetch(url);
    if(!res.ok) throw new Error('Failed to fetch study plans');
    return res.json();
}

export async function getStudyPlan(planId){
    const res = await fetch(`${API_URL}/api/study-plan/${planId}`);
    if(!res.ok) throw new Error('Failed to fetch study plan');
    return res.json();
}

export async function deleteStudyPlan(planId){
    const res = await fetch(`${API_URL}/api/study-plan/${planId}`, {
        method: 'DELETE',
    });
    if(!res.ok) throw new Error('Failed to delete study plan');
    return res.json();
};
