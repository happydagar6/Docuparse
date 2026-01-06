/**
 * Jest Unit Tests for Utilities
 * Tests helper functions and utilities
 */

describe('Utility Functions', () => {
  describe('String Utils', () => {
    it('should trim whitespace', () => {
      const trim = (str) => str.trim();
      
      expect(trim('  hello  ')).toBe('hello');
      expect(trim('\ntest\n')).toBe('test');
    });

    it('should capitalize string', () => {
      const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);
      
      expect(capitalize('hello')).toBe('Hello');
      expect(capitalize('WORLD')).toBe('WORLD');
    });

    it('should format title case', () => {
      const toTitleCase = (str) => 
        str.split(' ').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
        ).join(' ');
      
      expect(toTitleCase('hello world')).toBe('Hello World');
      expect(toTitleCase('research paper analysis')).toBe('Research Paper Analysis');
    });
  });

  describe('Array Utils', () => {
    it('should remove duplicates', () => {
      const removeDuplicates = (arr) => [...new Set(arr)];
      
      expect(removeDuplicates([1, 2, 2, 3, 3, 3])).toEqual([1, 2, 3]);
      expect(removeDuplicates(['a', 'b', 'a'])).toEqual(['a', 'b']);
    });

    it('should flatten nested array', () => {
      const flatten = (arr) => arr.flat(Infinity);
      
      expect(flatten([1, [2, [3, [4]]]])).toEqual([1, 2, 3, 4]);
      expect(flatten([[1], [2, 3], [[4]]])).toEqual([1, 2, 3, 4]);
    });

    it('should find unique elements', () => {
      const getUnique = (arr) => Array.from(new Set(arr));
      
      expect(getUnique([1, 1, 2, 2, 3])).toEqual([1, 2, 3]);
    });
  });

  describe('Object Utils', () => {
    it('should deep clone object', () => {
      const deepClone = (obj) => JSON.parse(JSON.stringify(obj));
      
      const original = { a: 1, b: { c: 2 } };
      const cloned = deepClone(original);
      
      cloned.b.c = 3;
      expect(original.b.c).toBe(2); // Original unchanged
    });

    it('should merge objects', () => {
      const merge = (obj1, obj2) => ({ ...obj1, ...obj2 });
      
      const result = merge(
        { a: 1, b: 2 },
        { b: 3, c: 4 }
      );
      
      expect(result).toEqual({ a: 1, b: 3, c: 4 });
    });

    it('should filter object properties', () => {
      const filterObject = (obj, predicate) =>
        Object.fromEntries(
          Object.entries(obj).filter(([, value]) => predicate(value))
        );
      
      const result = filterObject(
        { a: 1, b: 2, c: 3 },
        (val) => val > 1
      );
      
      expect(result).toEqual({ b: 2, c: 3 });
    });
  });

  describe('Date Utils', () => {
    it('should format date', () => {
      const formatDate = (date) => 
        new Date(date).toLocaleDateString('en-US');
      
      const date = new Date('2025-01-06');
      const formatted = formatDate(date);
      
      expect(formatted).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
    });

    it('should check if date is in past', () => {
      const isPast = (date) => new Date(date) < new Date();
      
      expect(isPast('2020-01-01')).toBe(true);
      expect(isPast('2030-01-01')).toBe(false);
    });

    it('should calculate days between dates', () => {
      const daysBetween = (date1, date2) => {
        const msPerDay = 24 * 60 * 60 * 1000;
        return Math.round(
          (new Date(date2) - new Date(date1)) / msPerDay
        );
      };
      
      expect(daysBetween('2025-01-01', '2025-01-06')).toBe(5);
    });
  });

  describe('Number Utils', () => {
    it('should format number to currency', () => {
      const formatCurrency = (num) => 
        new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
        }).format(num);
      
      const formatted = formatCurrency(1234.56);
      expect(formatted).toMatch(/\$1,234\.56/);
    });

    it('should round to decimal places', () => {
      const roundTo = (num, decimals) => 
        Math.round(num * Math.pow(10, decimals)) / Math.pow(10, decimals);
      
      expect(roundTo(3.14159, 2)).toBe(3.14);
      expect(roundTo(1.5555, 2)).toBe(1.56);
    });

    it('should check if number is prime', () => {
      const isPrime = (num) => {
        if (num <= 1) return false;
        if (num <= 3) return true;
        if (num % 2 === 0 || num % 3 === 0) return false;
        for (let i = 5; i * i <= num; i += 6) {
          if (num % i === 0 || num % (i + 2) === 0) return false;
        }
        return true;
      };
      
      expect(isPrime(2)).toBe(true);
      expect(isPrime(7)).toBe(true);
      expect(isPrime(10)).toBe(false);
    });
  });
});
