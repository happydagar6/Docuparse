const React = require('react');

module.exports = {
  Document: ({ children }) => React.createElement('div', { 'data-testid': 'mock-pdf-document' }, children),
  Page: () => React.createElement('div', { 'data-testid': 'mock-pdf-page' }, 'Mock PDF Page'),
  pdfjs: { GlobalWorkerOptions: {} }
};
