const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

const storage = multer.diskStorage({
  destination: os.tmpdir(),
  filename: function(req, file, cb) {
    cb(null, Date.now() + '_upload.txt');
  }
});
const upload = multer({ storage: storage });

app.use(express.static(path.join(__dirname)));

app.post('/api/build', upload.single('txtfile'), function(req, res) {
  if (!req.file) {
    res.status(400).send('No file uploaded.');
    return;
  }

  var txtPath = req.file.path;
  var htmlPath = txtPath.replace(/\.txt$/, '.html');
  var title    = (req.body.title    || '').trim() || 'Latin Poem';
  var subtitle = (req.body.subtitle || '').trim();

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  function send(obj) {
    res.write('data: ' + JSON.stringify(obj) + '\n\n');
  }

  var args = [path.join(__dirname, 'build.py'), txtPath, title];
  if (subtitle) args.push(subtitle);

  send({ line: '$ python3 build.py <file> "' + title + '"' + (subtitle ? ' "' + subtitle + '"' : '') });

  var proc = spawn('python3', args, { cwd: os.tmpdir() });

  proc.stdout.on('data', function(d) {
    d.toString().split('\n').filter(function(l) { return l.trim(); }).forEach(function(l) {
      send({ line: l });
    });
  });

  proc.stderr.on('data', function(d) {
    d.toString().split('\n').filter(function(l) { return l.trim(); }).forEach(function(l) {
      send({ line: l });
    });
  });

  proc.on('error', function(err) {
    send({ error: 'Failed to start build: ' + err.message });
    fs.unlink(txtPath, function() {});
    res.end();
  });

  proc.on('close', function(code) {
    fs.unlink(txtPath, function() {});

    if (code !== 0 || !fs.existsSync(htmlPath)) {
      send({ error: 'Build exited with code ' + code + '.' });
      res.end();
      return;
    }

    var html = fs.readFileSync(htmlPath, 'utf-8');
    fs.unlink(htmlPath, function() {});
    send({ done: true, html: Buffer.from(html).toString('base64') });
    res.end();
  });
});

app.listen(PORT, function() {
  console.log('Server running on port ' + PORT);
});
