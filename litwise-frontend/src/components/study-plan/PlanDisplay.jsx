'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { 
  Calendar, 
  Clock, 
  Target, 
  Lightbulb, 
  BookOpen, 
  CheckCircle2, 
  Sparkles, 
  Trophy,
  Flame,
  GraduationCap,
  Zap,
  Coffee,
  Scale,
  FileText
} from 'lucide-react';

const STYLE_CONFIG = {
  intensive: { icon: Zap, color: 'text-red-500' },
  balanced: { icon: Scale, color: 'text-blue-500' },
  light: { icon: Coffee, color: 'text-green-500' },
};

const EXAM_CONFIG = {
  school_test: { icon: BookOpen, label: 'School Test' },
  college_exam: { icon: GraduationCap, label: 'College Exam' },
  competitive: { icon: Trophy, label: 'Competitive' },
  certification: { icon: FileText, label: 'Certification' },
};

export default function PlanDisplay({ plan }) {
  const [completedDays, setCompletedDays] = useState(new Set());

  if (!plan) return null;

  const styleConfig = STYLE_CONFIG[plan.study_style] || STYLE_CONFIG.balanced;
  const examConfig = EXAM_CONFIG[plan.exam_type] || EXAM_CONFIG.college_exam;
  const StyleIcon = styleConfig.icon;
  const ExamIcon = examConfig.icon;

  const totalDays = plan.weeks?.reduce((acc, week) => acc + (week.days?.length || 0), 0) || 0;
  const progress = totalDays > 0 ? (completedDays.size / totalDays) * 100 : 0;

  const toggleDay = (weekNum, dayNum) => {
    const key = `${weekNum}-${dayNum}`;
    setCompletedDays(prev => {
      const newSet = new Set(prev);
      if (newSet.has(key)) newSet.delete(key);
      else newSet.add(key);
      return newSet;
    });
  };

  const isDayCompleted = (weekNum, dayNum) => completedDays.has(`${weekNum}-${dayNum}`);

  return (
    <div className="space-y-4">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <Card className="overflow-hidden border-0 shadow-lg">
          <div className="bg-linear-to-r from-teal-500 via-cyan-500 to-blue-500 p-5 text-white">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                    <Calendar className="h-5 w-5" />
                  </div>
                  <Badge className="bg-white/20 text-white border-white/30">{plan.duration_weeks} Week Plan</Badge>
                </div>
                <h2 className="text-xl font-bold mb-1 line-clamp-2">{plan.paper_title}</h2>
                <div className="flex flex-wrap items-center gap-3 mt-3">
                  <div className="flex items-center gap-1.5 text-sm text-white/90">
                    <ExamIcon className="h-4 w-4" />
                    <span>{examConfig.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm text-white/90">
                    <StyleIcon className="h-4 w-4" />
                    <span className="capitalize">{plan.study_style}</span>
                  </div>
                </div>
              </div>
              <div className="hidden sm:block">
                <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <Trophy className="h-8 w-8 text-white/90" />
                </div>
              </div>
            </div>
          </div>
          {/* Progress Bar */}
          <div className="p-4 bg-linear-to-r from-slate-50 to-white border-t">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Study Progress</span>
              <span className="text-sm font-semibold text-teal-600">{completedDays.size}/{totalDays} days</span>
            </div>
            <Progress value={progress} className="h-2" />
            {progress > 0 && (
              <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                <Flame className="h-3 w-3 text-orange-500" />
                Keep going! You&apos;re {Math.round(progress)}% through your plan.
              </p>
            )}
          </div>
        </Card>
      </motion.div>

      {/* Tips */}
      {plan.tips?.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
          <Card className="border-amber-200 bg-linear-to-br from-amber-50 to-yellow-50/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2 text-amber-700">
                <div className="p-1.5 bg-amber-100 rounded-lg">
                  <Lightbulb className="h-4 w-4 text-amber-600" />
                </div>
                Pro Study Tips
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <ul className="space-y-2">
                {plan.tips.map((tip, i) => (
                  <motion.li key={i} className="flex items-start gap-2 text-sm" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}>
                    <Sparkles className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                    <span className="text-amber-800">{tip}</span>
                  </motion.li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Weekly Plans */}
      <Accordion type="single" collapsible defaultValue="week-1" className="space-y-2">
        {plan.weeks?.map((week, weekIndex) => {
          const weekDaysCompleted = week.days?.filter(d => isDayCompleted(week.week, d.day)).length || 0;
          const weekTotalDays = week.days?.length || 0;
          const weekProgress = weekTotalDays > 0 ? (weekDaysCompleted / weekTotalDays) * 100 : 0;
          
          return (
            <motion.div key={week.week} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: weekIndex * 0.05 + 0.2 }}>
              <AccordionItem value={`week-${week.week}`} className="border rounded-xl px-4 shadow-sm hover:shadow-md transition-shadow">
                <AccordionTrigger className="hover:no-underline py-4">
                  <div className="flex items-center gap-4 flex-1">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg transition-all ${weekProgress === 100 ? 'bg-linear-to-br from-green-400 to-emerald-500 text-white shadow-lg shadow-green-200' : 'bg-linear-to-br from-teal-100 to-cyan-100 text-teal-700'}`}>
                      {weekProgress === 100 ? <CheckCircle2 className="h-6 w-6" /> : week.week}
                    </div>
                    <div className="text-left flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-gray-900">Week {week.week}</p>
                        {weekProgress === 100 && <Badge className="bg-green-100 text-green-700 text-xs">Done!</Badge>}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">{week.focus_area}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Progress value={weekProgress} className="h-1.5 flex-1 max-w-[100px]" />
                        <span className="text-xs text-muted-foreground">{weekDaysCompleted}/{weekTotalDays}</span>
                      </div>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2 pb-2">
                    {/* Goals */}
                    {week.goals?.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium flex items-center gap-1 mb-2 text-gray-700">
                          <Target className="h-3.5 w-3.5 text-teal-500" /> Weekly Goals
                        </h4>
                        <div className="grid gap-1.5">
                          {week.goals.map((goal, i) => (
                            <div key={i} className="flex items-start gap-2 p-2 bg-slate-50 rounded-lg text-sm text-gray-700">
                              <span className="text-teal-500">→</span> {goal}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Days */}
                    <div>
                      <h4 className="text-xs font-medium flex items-center gap-1 mb-2 text-gray-700">
                        <Calendar className="h-3.5 w-3.5 text-teal-500" /> Daily Schedule
                      </h4>
                      <div className="grid gap-3">
                        {week.days?.map((day) => {
                          const isCompleted = isDayCompleted(week.week, day.day);
                          return (
                            <div
                              key={day.day}
                              className={`rounded-xl transition-all duration-200 border-2 overflow-hidden ${isCompleted ? 'bg-linear-to-r from-green-50 to-emerald-50 border-green-200' : 'bg-white border-gray-100 hover:border-teal-200'}`}
                            >
                              {/* Day Header - Clickable */}
                              <motion.div
                                whileTap={{ scale: 0.99 }}
                                onClick={() => toggleDay(week.week, day.day)}
                                className="p-3 cursor-pointer"
                              >
                                <div className="flex items-center gap-3">
                                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all shrink-0 ${isCompleted ? 'bg-green-500 text-white' : 'bg-linear-to-br from-teal-100 to-cyan-100 text-teal-600'}`}>
                                    {isCompleted ? <CheckCircle2 className="h-5 w-5" /> : <span className="text-sm font-bold">{day.day}</span>}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                      <span className={`font-semibold ${isCompleted ? 'text-green-700' : 'text-gray-900'}`}>Day {day.day}</span>
                                      <Badge variant="secondary" className={`text-xs ${isCompleted ? 'bg-green-100 text-green-700' : 'bg-teal-100 text-teal-700'}`}>
                                        <Clock className="h-3 w-3 mr-1" />{day.duration_hours}h
                                      </Badge>
                                    </div>
                                    <p className={`text-sm font-medium ${isCompleted ? 'text-green-600' : 'text-gray-700'}`}>
                                      {day.topics?.join(' • ')}
                                    </p>
                                  </div>
                                </div>
                              </motion.div>
                              
                              {/* Tasks Section */}
                              {day.tasks?.length > 0 && (
                                <div className={`px-3 pb-3 pt-0 border-t ${isCompleted ? 'border-green-200' : 'border-gray-100'}`}>
                                  <h5 className={`text-xs font-medium mt-2 mb-2 flex items-center gap-1 ${isCompleted ? 'text-green-600' : 'text-gray-500'}`}>
                                    <CheckCircle2 className="h-3 w-3" /> Tasks to Complete:
                                  </h5>
                                  <ul className="space-y-1.5">
                                    {day.tasks.map((task, taskIndex) => (
                                      <li key={taskIndex} className={`text-sm flex items-start gap-2 ${isCompleted ? 'text-green-700' : 'text-gray-600'}`}>
                                        <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${isCompleted ? 'bg-green-400' : 'bg-teal-400'}`}></span>
                                        <span>{task}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Revision */}
                    {week.revision_topics?.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium flex items-center gap-1 mb-2 text-gray-700">
                          <BookOpen className="h-3.5 w-3.5 text-purple-500" /> Revision Focus
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {week.revision_topics.map((topic, i) => (
                            <Badge key={i} variant="secondary" className="bg-purple-50 text-purple-700 border border-purple-200 text-xs">{topic}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </motion.div>
          );
        })}
      </Accordion>

      {/* Completion Message */}
      <AnimatePresence>
        {progress === 100 && (
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
            <Card className="bg-linear-to-r from-green-500 to-emerald-500 text-white border-0 shadow-xl">
              <CardContent className="p-6 text-center">
                <Trophy className="h-12 w-12 mx-auto mb-3 text-yellow-300" />
                <h3 className="text-xl font-bold mb-2">Congratulations! 🎉</h3>
                <p className="text-white/90">You&apos;ve completed your entire study plan!</p>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}