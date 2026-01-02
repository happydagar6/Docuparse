'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import dynamic from 'next/dynamic';
import { getStudyPlans, deleteStudyPlan } from '@/app/api/study-plan';
import { PageLayout } from '@/components/layout/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Calendar, 
  FileText, 
  Sparkles, 
  Clock,
  Trash2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Lazy load heavy components
const PlanGenerator = dynamic(() => import('@/components/study-plan/PlanGenerator'), {
  loading: () => <div className="flex justify-center p-8"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>
});
const PlanDisplay = dynamic(() => import('@/components/study-plan/PlanDisplay'), {
  loading: () => <div className="flex justify-center p-8"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>
});

// Additional icons
const LazyIcons = dynamic(() => import('lucide-react').then(mod => ({
  BookOpen: mod.BookOpen,
  ChevronRight: mod.ChevronRight,
  GraduationCap: mod.GraduationCap,
  Loader2: mod.Loader2
})), { ssr: false });

import { formatDistanceToNow } from 'date-fns';
import { GraduationCap } from 'lucide-react';
import { History } from 'lucide-react';
import { BookOpen } from 'lucide-react';
import { ChevronRight } from 'lucide-react';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Loader2 } from 'lucide-react';

export default function StudyPlanPage() {
  const [currentPlan, setCurrentPlan] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [planToDelete, setPlanToDelete] = useState(null);
  
  const queryClient = useQueryClient();

  const { data, refetch } = useQuery({
    queryKey: ['study-plans'],
    queryFn: () => getStudyPlans(),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStudyPlan,
    onSuccess: () => {
      toast.success('Study plan deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['study-plans'] });
      // Clear current plan if it was the deleted one
      if (selectedPlanId === planToDelete?.id) {
        setCurrentPlan(null);
        setSelectedPlanId(null);
      }
      setDeleteDialogOpen(false);
      setPlanToDelete(null);
    },
    onError: () => {
      toast.error('Failed to delete study plan');
    },
  });

  const plans = data?.plans || [];

  const handlePlanGenerated = (plan) => {
    setCurrentPlan(plan);
    setSelectedPlanId(null);
    refetch();
  };

  const handleSelectPlan = (plan) => {
    const planData = typeof plan.plan_data === 'string' 
      ? JSON.parse(plan.plan_data) 
      : plan.plan_data;
    setCurrentPlan(planData);
    setSelectedPlanId(plan.id);
  };

  const handleDeleteClick = (e, plan) => {
    e.stopPropagation(); // Prevent selecting the plan
    setPlanToDelete(plan);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (planToDelete) {
      deleteMutation.mutate(planToDelete.id);
    }
  };

  return (
    <PageLayout>
      {/* Enhanced Header Section */}
      <div className="mb-8">
        <div className="relative bg-linear-to-br from-teal-50 via-cyan-50 to-blue-50 rounded-2xl p-8 md:p-10 border border-teal-100/50 overflow-hidden">
          {/* Glassmorphic background elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-linear-to-br from-teal-200 to-cyan-200 rounded-full blur-3xl opacity-20 -z-10"></div>
          <div className="absolute bottom-0 left-0 w-48 h-48 bg-linear-to-tr from-cyan-200 to-blue-200 rounded-full blur-3xl opacity-15 -z-10"></div>
          
          <div className="relative z-10 flex items-start gap-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-white/60 backdrop-blur-md border border-white/40 shadow-lg">
              <GraduationCap className="h-7 w-7 text-teal-600" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">Study Plan Generator</h1>
              <p className="text-gray-700 leading-relaxed">Create personalized, AI-powered study plans tailored to your learning goals and document content.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left Column: Generator + History */}
        <div className="space-y-4">
          <PlanGenerator onPlanGenerated={handlePlanGenerated} />

          {/* History */}
          <AnimatePresence>
            {plans.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="border-0 shadow-lg overflow-hidden">
                  <CardHeader className="pb-3 bg-linear-to-r from-slate-50 to-gray-50 border-b">
                    <CardTitle className="text-sm flex items-center gap-2 text-gray-700">
                      <div className="p-1.5 bg-white rounded-lg shadow-sm">
                        <History className="h-4 w-4 text-slate-600" />
                      </div>
                      Recent Study Plans
                      <Badge variant="secondary" className="ml-auto bg-slate-200 text-slate-600">
                        {plans.length}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-[280px]">
                      <div className="p-2">
                        {plans.map((plan, index) => {
                          const isSelected = selectedPlanId === plan.id;
                          return (
                            <motion.div
                              key={plan.id}
                              initial={{ opacity: 0, x: -20 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: index * 0.05 }}
                              className={`relative group w-full p-3 mb-2 rounded-xl text-left transition-all duration-200 ${isSelected ? 'bg-linear-to-r from-teal-50 to-cyan-50 border-2 border-teal-200 shadow-md' : 'bg-white hover:bg-slate-50 border border-gray-100 hover:border-gray-200 hover:shadow-sm'}`}
                            >
                              <button
                                onClick={() => handleSelectPlan(plan)}
                                className="w-full text-left"
                              >
                                <div className="flex items-start gap-3">
                                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${isSelected ? 'bg-linear-to-br from-teal-500 to-cyan-500 text-white shadow-lg shadow-teal-200' : 'bg-slate-100 text-slate-500'}`}>
                                    <BookOpen className="h-5 w-5" />
                                  </div>
                                  <div className="flex-1 min-w-0 pr-8">
                                    <p className={`text-sm font-medium truncate ${isSelected ? 'text-teal-700' : 'text-gray-900'}`}>
                                      {plan.paper_title}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                                      <Badge variant="secondary" className={`text-xs ${isSelected ? 'bg-teal-100 text-teal-700' : 'bg-slate-100'}`}>
                                        <Calendar className="h-3 w-3 mr-1" />
                                        {plan.duration_weeks}w
                                      </Badge>
                                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Clock className="h-3 w-3" />
                                        {formatDistanceToNow(new Date(plan.created_at), { addSuffix: true })}
                                      </span>
                                    </div>
                                  </div>
                                  <ChevronRight className={`h-4 w-4 mt-1 shrink-0 transition-colors ${isSelected ? 'text-teal-500' : 'text-gray-300'}`} />
                                </div>
                              </button>
                              
                              {/* Delete Button */}
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={(e) => handleDeleteClick(e, plan)}
                                className="absolute top-2 right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity bg-red-50 hover:bg-red-100 text-red-500 hover:text-red-600"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </motion.div>
                          );
                        })}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right Column: Plan Display */}
        <div className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {currentPlan ? (
              <motion.div
                key="plan"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <PlanDisplay plan={currentPlan} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Card className="h-[500px] flex items-center justify-center border-2 border-dashed border-gray-200 bg-linear-to-br from-slate-50 to-gray-50/50">
                  <div className="text-center px-6">
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.2, type: "spring" }}
                      className="w-24 h-24 mx-auto mb-6 rounded-3xl bg-linear-to-br from-teal-100 to-cyan-100 flex items-center justify-center shadow-lg shadow-teal-100"
                    >
                      <GraduationCap className="h-12 w-12 text-teal-600" />
                    </motion.div>
                    <motion.h3
                      initial={{ y: 10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.3 }}
                      className="text-xl font-semibold text-gray-800 mb-2"
                    >
                      Create Your Study Plan
                    </motion.h3>
                    <motion.p
                      initial={{ y: 10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.4 }}
                      className="text-muted-foreground max-w-sm mx-auto mb-6"
                    >
                      Select a document and customize your preferences to generate a personalized AI-powered study schedule.
                    </motion.p>
                    <motion.div
                      initial={{ y: 10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      transition={{ delay: 0.5 }}
                      className="flex items-center justify-center gap-4 text-sm text-muted-foreground"
                    >
                      <div className="flex items-center gap-1.5">
                        <Sparkles className="h-4 w-4 text-teal-500" />
                        <span>AI-Powered</span>
                      </div>
                      <div className="w-1 h-1 rounded-full bg-gray-300" />
                      <div className="flex items-center gap-1.5">
                        <Calendar className="h-4 w-4 text-cyan-500" />
                        <span>Customizable</span>
                      </div>
                      <div className="w-1 h-1 rounded-full bg-gray-300" />
                      <div className="flex items-center gap-1.5">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <span>Document-Based</span>
                      </div>
                    </motion.div>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <div className="p-2 bg-red-100 rounded-lg">
                <Trash2 className="h-5 w-5 text-red-600" />
              </div>
              Delete Study Plan
            </AlertDialogTitle>
            <AlertDialogDescription className="pt-2">
              Are you sure you want to delete the study plan for{' '}
              <span className="font-semibold text-gray-700">
                &quot;{planToDelete?.paper_title}&quot;
              </span>
              ? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Plan
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageLayout>
  );
}