'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen, 
  Sparkles, 
  Calendar, 
  Users, 
  Link2,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  ExternalLink,
  Quote,
  TrendingUp,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { useCitationStore } from '@/lib/stores';

const CitationTypeColors = {
  background: 'bg-blue-100 text-blue-800 border-blue-300',
  method: 'bg-green-100 text-green-800 border-green-300',
  comparison: 'bg-purple-100 text-purple-800 border-purple-300',
  data: 'bg-orange-100 text-orange-800 border-orange-300',
  unknown: 'bg-gray-100 text-gray-800 border-gray-300'
};

export function CitationCard({ citation, isSelected, onToggleSelect }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="mb-4"
    >
      <Card className={`hover:shadow-md transition-shadow ${isSelected ? 'ring-2 ring-blue-500' : ''}`}>
        <CardContent className="p-4">
          {/* Header with checkbox and importance */}
          <div className="flex items-start gap-3 mb-3">
            <Checkbox
              checked={isSelected}
              onCheckedChange={() => onToggleSelect(citation.id)}
              className="mt-1"
            />
            
            <div className="flex-1">
              {/* Title */}
              <h3 className="font-semibold text-lg mb-2 leading-tight">
                {citation.title || (
                  <span className="text-gray-500 italic">
                    {citation.citation_text?.slice(0, 100)}
                    {citation.citation_text?.length > 100 ? '...' : ''}
                  </span>
                )}
              </h3>
              
              {/* Metadata row */}
              <div className="flex flex-wrap gap-2 mb-2">
                {/* Authors */}
                {citation.authors && citation.authors.length > 0 && (
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    <Users className="w-3 h-3" />
                    <span>
                      {citation.authors.slice(0, 3).join(', ')}
                      {citation.authors.length > 3 && ' et al.'}
                    </span>
                  </div>
                )}
                
                {/* Year */}
                {citation.year && (
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    <Calendar className="w-3 h-3" />
                    <span>{citation.year}</span>
                  </div>
                )}
                
                {/* Venue */}
                {citation.venue && (
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    <BookOpen className="w-3 h-3" />
                    <span className="truncate max-w-[200px]">{citation.venue}</span>
                  </div>
                )}
              </div>
              
              {/* Badges */}
              <div className="flex flex-wrap gap-2 mb-3">
                {/* Citation type */}
                {citation.citation_type && (
                  <Badge 
                    variant="outline"
                    className={CitationTypeColors[citation.citation_type] || CitationTypeColors.unknown}
                  >
                    {citation.citation_type}
                  </Badge>
                )}
                
                {/* Importance score */}
                <Badge variant="outline" className="bg-yellow-50 text-yellow-800 border-yellow-300">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  {(citation.importance_score * 100).toFixed(0)}% importance
                </Badge>
                
                {/* Mention count */}
                {citation.mention_count > 1 && (
                  <Badge variant="outline" className="bg-purple-50 text-purple-800 border-purple-300">
                    <Quote className="w-3 h-3 mr-1" />
                    {citation.mention_count} mentions
                  </Badge>
                )}
              </div>
              
              {/* AI Relevance Summary */}
              {citation.relevance_summary && (
                <div className="bg-linear-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-3 mb-3">
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                    <p className="text-sm text-gray-700 leading-relaxed">
                      <span className="font-semibold text-blue-700">AI Insight: </span>
                      {citation.relevance_summary}
                    </p>
                  </div>
                </div>
              )}
              
              {/* In-text references */}
              {citation.in_text_refs && citation.in_text_refs.length > 0 && (
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                  <span>Referenced as:</span>
                  {citation.in_text_refs.map((ref, idx) => (
                    <code key={idx} className="bg-gray-100 px-2 py-0.5 rounded">
                      {ref}
                    </code>
                  ))}
                </div>
              )}
              
              {/* Action buttons */}
              <div className="flex gap-2">
                {citation.doi && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => window.open(`https://doi.org/${citation.doi}`, '_blank')}
                  >
                    <Link2 className="w-3 h-3 mr-1" />
                    DOI
                  </Button>
                )}
                
                {citation.citation_context && citation.citation_context.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setExpanded(!expanded)}
                  >
                    {expanded ? <ChevronDown className="w-3 h-3 mr-1" /> : <ChevronRight className="w-3 h-3 mr-1" />}
                    Context ({citation.citation_context.length})
                  </Button>
                )}
              </div>
              
              {/* Expanded context */}
              <AnimatePresence>
                {expanded && citation.citation_context && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="mt-3 space-y-2"
                  >
                    <p className="text-xs font-semibold text-gray-600">Citation Context:</p>
                    {citation.citation_context.map((context, idx) => (
                      <div key={idx} className="bg-gray-50 p-2 rounded text-xs text-gray-700 border-l-2 border-blue-400">
                        ...{context}...
                      </div>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
          
          {/* Full citation text (collapsed by default) */}
          <details className="mt-2">
            <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
              View full citation text
            </summary>
            <p className="text-xs text-gray-600 mt-2 p-2 bg-gray-50 rounded border">
              {citation.citation_text}
            </p>
          </details>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function CitationList({ paperId, citations, isLoading }) {
  const { 
    selectedCitations, 
    toggleCitationSelection, 
    selectAllCitations, 
    clearSelection,
    filterType,
    sortBy 
  } = useCitationStore();
  
  // Use useMemo for derived state - no need for useState + useEffect
  const filteredCitations = useMemo(() => {
    if (!citations) return [];
    
    let filtered = [...citations];
    
    // Filter by type
    if (filterType !== 'all') {
      filtered = filtered.filter(c => c.citation_type === filterType);
    }
    
    // Sort
    filtered.sort((a, b) => {
      if (sortBy === 'importance') {
        return (b.importance_score || 0) - (a.importance_score || 0);
      } else if (sortBy === 'year') {
        return (b.year || 0) - (a.year || 0);
      } else if (sortBy === 'mentions') {
        return (b.mention_count || 0) - (a.mention_count || 0);
      }
      return 0;
    });
    
    return filtered;
  }, [citations, filterType, sortBy]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading citations...</span>
      </div>
    );
  }

  if (!citations || citations.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No citations found</p>
          <p className="text-sm text-gray-500">
            This paper may not have a references section, or citations haven&apos;t been extracted yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div>
      {/* Selection controls */}
      {selectedCitations.length > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
          <span className="text-sm font-medium text-blue-800">
            {selectedCitations.length} citation{selectedCitations.length > 1 ? 's' : ''} selected
          </span>
          <Button variant="ghost" size="sm" onClick={clearSelection}>
            Clear selection
          </Button>
        </div>
      )}
      
      {/* Quick select all */}
      <div className="mb-4 flex items-center gap-2">
        <Checkbox
          checked={selectedCitations.length === filteredCitations.length && filteredCitations.length > 0}
          onCheckedChange={(checked) => {
            if (checked) {
              selectAllCitations(filteredCitations.map(c => c.id));
            } else {
              clearSelection();
            }
          }}
        />
        <span className="text-sm text-gray-600">Select all ({filteredCitations.length})</span>
      </div>
      
      {/* Citation cards */}
      <AnimatePresence>
        {filteredCitations.map((citation) => (
          <CitationCard
            key={citation.id}
            citation={citation}
            isSelected={selectedCitations.includes(citation.id)}
            onToggleSelect={toggleCitationSelection}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}