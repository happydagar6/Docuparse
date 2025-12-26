/**
 * Enhanced Interactive Footer Component
 * 
 * A beautiful footer with feedback functionality, proper spacing from sidebar,
 * and interactive elements while maintaining clean design.
 */

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen,
  Mail,
  Twitter,
  Linkedin,
  Github,
  Heart,
  Send,
  MessageCircle,
  ExternalLink,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';

const InteractiveFooter = () => {
  const currentYear = new Date().getFullYear();
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackForm, setFeedbackForm] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [newsletterEmail, setNewsletterEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null);

  const socialLinks = [
    { 
      name: 'GitHub', 
      icon: Github, 
      href: 'https://github.com/happydagar6',
      color: 'hover:bg-gray-800 hover:text-white'
    },
    { 
      name: 'Twitter', 
      icon: Twitter, 
      href: '#',
      color: 'hover:bg-blue-500 hover:text-white'
    },
    { 
      name: 'LinkedIn', 
      icon: Linkedin, 
      href: 'https://www.linkedin.com/in/kapil-dagar',
      color: 'hover:bg-blue-600 hover:text-white'
    },
    { 
      name: 'Email', 
      icon: Mail, 
      href: 'mailto:harshitdagar913@gmail.com',
      color: 'hover:bg-red-500 hover:text-white'
    }
  ];

  const quickLinks = [
    { name: 'About', href: '#about' },
    { name: 'Privacy Policy', href: '#privacy' },
    { name: 'Terms of Service', href: '#terms' },
    { name: 'Support', href: '#support' },
    { name: 'Documentation', href: '#docs' }
  ];

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!feedbackForm.name || !feedbackForm.email || !feedbackForm.message) {
      setSubmitStatus({ type: 'error', message: 'Please fill in all fields' });
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus(null);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...feedbackForm, type: 'feedback' })
      });

      const data = await response.json();

      if (response.ok) {
        setSubmitStatus({ type: 'success', message: data.message });
        setFeedbackForm({ name: '', email: '', message: '' });
        setTimeout(() => setShowFeedback(false), 2000);
      } else {
        setSubmitStatus({ type: 'error', message: data.error });
      }
    } catch (error) {
      setSubmitStatus({ type: 'error', message: 'Failed to send feedback' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNewsletterSubmit = async (e) => {
    e.preventDefault();
    if (!newsletterEmail) return;

    setIsSubmitting(true);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name: 'Newsletter Subscriber',
          email: newsletterEmail, 
          message: 'Newsletter subscription request',
          type: 'newsletter'
        })
      });

      const data = await response.json();

      if (response.ok) {
        setSubmitStatus({ type: 'success', message: 'Subscribed successfully!' });
        setNewsletterEmail('');
      } else {
        setSubmitStatus({ type: 'error', message: data.error });
      }
    } catch (error) {
      setSubmitStatus({ type: 'error', message: 'Subscription failed' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <footer className="w-full bg-white border-t border-gray-200 mt-auto relative">
      {/* Main Footer Content - with proper sidebar spacing */}
      <div className="lg:ml-64 max-w-none px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Brand Section */}
          <div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="flex items-center mb-3">
                <div className="w-8 h-8 bg-linear-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center mr-2">
                  <BookOpen className="h-5 w-5 text-white" />
                </div>
                <span className="text-xl font-bold bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  Litwise
                </span>
              </div>
              <p className="text-gray-600 text-sm mb-4 leading-relaxed">
                AI-powered research assistant helping researchers accelerate discoveries.
              </p>
              
              {/* Social Links */}
              <div className="flex gap-2">
                {socialLinks.map((social) => {
                  const IconComponent = social.icon;
                  return (
                    <motion.a
                      key={social.name}
                      href={social.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      whileHover={{ scale: 1.1, y: -2 }}
                      whileTap={{ scale: 0.95 }}
                      className={`w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center transition-all duration-300 ${social.color}`}
                      aria-label={social.name}
                    >
                      <IconComponent className="h-4 w-4" />
                    </motion.a>
                  );
                })}
              </div>
            </motion.div>
          </div>

          {/* Newsletter */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-3 text-sm">Stay Updated</h4>
            <p className="text-gray-600 text-xs mb-3">
              Get the latest updates on AI research tools.
            </p>
            <form onSubmit={handleNewsletterSubmit} className="space-y-2">
              <Input
                type="email"
                placeholder="Enter your email"
                value={newsletterEmail}
                onChange={(e) => setNewsletterEmail(e.target.value)}
                className="w-full h-9 text-sm"
                disabled={isSubmitting}
              />
              <Button 
                type="submit" 
                className="w-full h-9 text-sm bg-linear-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                disabled={!newsletterEmail || isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-3 w-3 animate-spin mr-2" />
                ) : (
                  <Send className="h-3 w-3 mr-2" />
                )}
                Subscribe
              </Button>
            </form>
          </div>

          {/* Feedback Section */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-3 text-sm">Feedback</h4>
            <p className="text-gray-600 text-xs mb-3">
              Help us improve by sharing your thoughts.
            </p>
            <Button 
              onClick={() => setShowFeedback(true)}
              variant="outline"
              className="w-full h-9 text-sm hover:bg-blue-50 hover:border-blue-300"
            >
              <MessageCircle className="h-3 w-3 mr-2" />
              Send Feedback
            </Button>
          </div>
        </div>

        {/* Bottom Bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-6 pt-4 border-t border-gray-200"
        >
          <div className="flex flex-col md:flex-row justify-between items-center gap-3">
            <div className="flex items-center text-xs text-gray-600">
              © {currentYear} Litwise AI. Made with
              <Heart className="inline h-3 w-3 text-red-500 mx-1" />
              for researchers worldwide.
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>🚀 React 19.2</span>
              <span>⚡ Next.js 16</span>
              <span>🤖 AI-Powered</span>
            </div>
          </div>
        </motion.div>
        </div>
      </div>

      {/* Feedback Modal */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={() => setShowFeedback(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md"
            >
              <Card>
                <CardContent className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Send Feedback</h3>
                  
                  <form onSubmit={handleFeedbackSubmit} className="space-y-4">
                    <div>
                      <Input
                        placeholder="Your name"
                        value={feedbackForm.name}
                        onChange={(e) => setFeedbackForm(prev => ({...prev, name: e.target.value}))}
                        disabled={isSubmitting}
                      />
                    </div>
                    <div>
                      <Input
                        type="email"
                        placeholder="Your email"
                        value={feedbackForm.email}
                        onChange={(e) => setFeedbackForm(prev => ({...prev, email: e.target.value}))}
                        disabled={isSubmitting}
                      />
                    </div>
                    <div>
                      <Textarea
                        placeholder="Your feedback..."
                        rows={4}
                        value={feedbackForm.message}
                        onChange={(e) => setFeedbackForm(prev => ({...prev, message: e.target.value}))}
                        disabled={isSubmitting}
                      />
                    </div>

                    {submitStatus && (
                      <div className={`flex items-center gap-2 text-sm ${
                        submitStatus.type === 'success' ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {submitStatus.type === 'success' ? 
                          <CheckCircle className="h-4 w-4" /> : 
                          <AlertCircle className="h-4 w-4" />
                        }
                        {submitStatus.message}
                      </div>
                    )}

                    <div className="flex gap-3 pt-2">
                      <Button 
                        type="submit" 
                        className="flex-1"
                        disabled={isSubmitting || !feedbackForm.name || !feedbackForm.email || !feedbackForm.message}
                      >
                        {isSubmitting ? (
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Send className="h-4 w-4 mr-2" />
                        )}
                        Send
                      </Button>
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => setShowFeedback(false)}
                        disabled={isSubmitting}
                      >
                        Cancel
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Status Toast */}
      <AnimatePresence>
        {submitStatus && !showFeedback && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            className="fixed bottom-4 right-4 z-50"
          >
            <div className={`px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 ${
              submitStatus.type === 'success' 
                ? 'bg-green-600 text-white' 
                : 'bg-red-600 text-white'
            }`}>
              {submitStatus.type === 'success' ? 
                <CheckCircle className="h-5 w-5" /> : 
                <AlertCircle className="h-5 w-5" />
              }
              {submitStatus.message}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </footer>
  );
};

export default InteractiveFooter;