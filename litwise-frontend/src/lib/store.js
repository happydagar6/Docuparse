import { create } from "zustand";

export const useStore = create((set) => ({
    highlights: [],
    setHighlights: (highlights) => set({ highlights }),

    toggleHighlight: (index) => set((state) => {
        highlights: state.highlights.includes(index) ? state.highlights.filter(h => h !== index) : [...state.highlights, index]
    })
}));