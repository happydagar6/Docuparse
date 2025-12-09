'use client';

import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Calendar, 
  BookOpen, 
  Award,
  PieChart,
  BarChart3
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function CitationStats({ stats, isLoading }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="h-20 bg-gray-200 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  const statCards = [
    {
      title: 'Total Citations',
      value: stats.total_citations || 0,
      icon: BookOpen,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      title: 'Average Year',
      value: stats.average_citation_year ? Math.round(stats.average_citation_year) : 'N/A',
      icon: Calendar,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      title: 'Top Cited Works',
      value: stats.top_cited_works?.length || 0,
      icon: Award,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    }
  ];

  return (
    <div className="space-y-6 mb-6">
      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {statCards.map((stat, idx) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
          >
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{stat.title}</p>
                    <p className="text-3xl font-bold">{stat.value}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
      
      {/* Citations by type */}
      {stats.citations_by_type && Object.keys(stats.citations_by_type).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="w-5 h-5" />
              Citations by Type
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.citations_by_type).map(([type, count]) => (
                <Badge key={type} variant="outline" className="px-4 py-2 text-sm">
                  <span className="font-semibold">{type}:</span>
                  <span className="ml-2">{count}</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Top cited works */}
      {stats.top_cited_works && stats.top_cited_works.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="w-5 h-5" />
              Most Important Citations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.top_cited_works.slice(0, 5).map((work, idx) => (
                <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <div className="shrink-0 w-8 h-8 bg-linear-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center text-white font-bold">
                    {idx + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{work.title || 'Untitled'}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {work.authors && work.authors.length > 0 && (
                        <span className="text-xs text-gray-600">
                          {work.authors.slice(0, 2).join(', ')}
                          {work.authors.length > 2 && ' et al.'}
                        </span>
                      )}
                      {work.year && (
                        <span className="text-xs text-gray-600">({work.year})</span>
                      )}
                    </div>
                  </div>
                  <div className="shrink-0">
                    <Badge variant="outline" className="bg-yellow-50">
                      {(work.importance_score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}