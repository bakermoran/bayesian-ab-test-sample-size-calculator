// Drop a CSV anywhere on the page to fill the upload form's file input.
(function () {
  var overlay = document.getElementById('drop-overlay');
  var input = document.querySelector('input[type="file"]');
  if (!overlay || !input) { return; }

  var depth = 0;

  function hasFiles(event) {
    var types = event.dataTransfer && event.dataTransfer.types;
    return !!types && Array.prototype.indexOf.call(types, 'Files') !== -1;
  }

  window.addEventListener('dragenter', function (event) {
    if (!hasFiles(event)) { return; }
    event.preventDefault();
    depth += 1;
    overlay.hidden = false;
  });

  window.addEventListener('dragover', function (event) {
    if (!hasFiles(event)) { return; }
    // Required, or the browser won't allow a drop and opens the file instead
    event.preventDefault();
  });

  window.addEventListener('dragleave', function (event) {
    if (!hasFiles(event)) { return; }
    depth = Math.max(0, depth - 1);
    if (depth === 0) { overlay.hidden = true; }
  });

  window.addEventListener('drop', function (event) {
    if (!hasFiles(event)) { return; }
    event.preventDefault();
    depth = 0;
    overlay.hidden = true;
    var file = event.dataTransfer.files[0];
    if (!file) { return; }
    var transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.focus();
  });
})();
