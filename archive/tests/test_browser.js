const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ args: ['--no-sandbox'] });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.toString()));
  
  await page.goto('http://localhost:8000/studio.html', { waitUntil: 'networkidle0' });
  
  // Click register tab
  await page.click('#tab-register');
  
  // Fill form
  await page.type('#reg-name', 'Test Studio');
  await page.type('#reg-email', 'test@test.com');
  await page.type('#reg-password', 'password123');
  
  // Click submit
  await page.click('#register-form button[type="submit"]');
  
  await new Promise(r => setTimeout(r, 2000));
  
  await browser.close();
})();
