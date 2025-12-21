import { apiRequest } from '@/lib/api';

export async function generateStudyPlan(data) {
    return apiRequest('/api/study-plan/generate', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function getStudyPlans(paperId = null){
    const url = paperId
        ? `/api/study-plan/list?paper_id=${paperId}`
        : '/api/study-plan/list';
    
    return apiRequest(url);
}

export async function getStudyPlan(planId){
    return apiRequest(`/api/study-plan/${planId}`);
}

export async function deleteStudyPlan(planId){
    return apiRequest(`/api/study-plan/${planId}`, {
        method: 'DELETE',
    });
}
