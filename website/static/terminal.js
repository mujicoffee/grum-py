async function loadPyodideAndPackages() {
    let pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.22.0/full/",
    });
    return pyodide;
}

let pyodideReadyPromise = loadPyodideAndPackages();

const pythonEditor = CodeMirror.fromTextArea(document.getElementById("python-code"), {
    mode: { name: "python", version: 3, singleLineStringErrors: false },
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    extraKeys: { "Ctrl-Space": "autocomplete" },
    gutters: ["CodeMirror-lint-markers"],
});

let runningCode = false;
let stopRequested = false;
let progressInterval;

const htmlEditor = CodeMirror.fromTextArea(document.getElementById("html-code"), {
    mode: "xml",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    extraKeys: { "Ctrl-Space": "autocomplete" },
});

const cssEditor = CodeMirror.fromTextArea(document.getElementById("css-code"), {
    mode: "css",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    extraKeys: { "Ctrl-Space": "autocomplete" },
});

const jsEditor = CodeMirror.fromTextArea(document.getElementById("js-code"), {
    mode: "javascript",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    extraKeys: { "Ctrl-Space": "autocomplete" },
});

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function () {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        this.classList.add('active');
        document.getElementById(this.getAttribute('data-tab')).classList.add('active');
        clearOutput();
    });
});

pythonEditor.getWrapperElement().style.height = '100%'; // or any height you want

// Create a Blob containing the Web Worker code
const workerBlob = new Blob([`
    importScripts('https://cdn.jsdelivr.net/pyodide/v0.22.0/full/pyodide.js');

    let pyodideReadyPromise = loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.22.0/full/",
    });

    self.onmessage = async (event) => {
      let { code, stopRequested } = event.data;

      try {
        let pyodide = await pyodideReadyPromise;
        pyodide.globals.set("code", code);
        pyodide.globals.set("stop_requested", stopRequested);

        let result = await pyodide.runPythonAsync(\`
            import sys
            import io
            import time

            original_stdout = sys.stdout
            sys.stdout = io.StringIO()

            def check_stop():
                if stop_requested:
                    raise Exception("Execution stopped by user")

            def limited_exec(code, line_limit, time_limit):
                start_time = time.time()
                line_count = 0
                last_check_time = start_time

                def trace_func(frame, event, arg):
                    nonlocal line_count, last_check_time
                    line_count += 1
                    current_time = time.time()
                    
                    if line_count > line_limit:
                        raise Exception(f"Execution exceeded {line_limit} lines")
                    
                    if current_time - start_time > time_limit:
                        raise Exception(f"Execution time exceeded {time_limit} seconds")
                    
                    if current_time - last_check_time > 0.1:  # Check every 0.1 seconds
                        check_stop()
                        last_check_time = current_time
                    
                    return trace_func

                sys.settrace(trace_func)
                try:
                    exec(code)
                finally:
                    sys.settrace(None)

            try:
                limited_exec(code, line_limit= 1000, time_limit=10)  # 10 seconds time limit
                output = sys.stdout.getvalue()
            except Exception as e:
                output = str(e)
            finally:
                sys.stdout = original_stdout

            output
        \`);

        self.postMessage({ result });
      } catch (err) {
        self.postMessage({ error: err.toString() });
      }
    };
`], { type: 'application/javascript' });

// Create a Web Worker from the Blob
const worker = new Worker(URL.createObjectURL(workerBlob));

worker.onmessage = function(event) {
    const { result, error } = event.data;
    clearInterval(progressInterval);
    runningCode = false;
    stopRequested = false;
    document.getElementById("run-button").disabled = false;

    if (error) {
        document.getElementById("output-pre").innerText = "Error: " + error;
    } else {
        document.getElementById("output-pre").innerText = result;
    }
};

async function runCode() {
    const activeTab = document.querySelector(".tab.active").getAttribute("data-tab");
    if (activeTab === "python-tab") {
        document.getElementById("output-iframe").style.display = "none";
        const pre = document.getElementById("output-pre");
        pre.style.display = "block";
    } else {
        document.getElementById("output-pre").style.display = "none";
        document.getElementById("output-iframe").style.display = "block";
    }

    if (runningCode) return;
    runningCode = true;
    stopRequested = false;
    document.getElementById("run-button").disabled = true;

    let code = pythonEditor.getValue();
    worker.postMessage({ code, stopRequested });
}

function stopCode() {
    stopRequested = true;
    worker.postMessage({ stopRequested: true });
}

document.getElementById("run-button").addEventListener("click", runCode);

function clearOutput() {
    document.getElementById("output-pre").textContent = "";
    document.getElementById("output-iframe").srcdoc = "";
}

document.getElementById("run-button-2").addEventListener("click", () => {
    const htmlContent = htmlEditor.getValue();
    const cssContent = `<style>${cssEditor.getValue()}</style>`;
    const jsContent = `<script>${jsEditor.getValue()}<\/script>`;
    
    document.getElementById("output-pre").style.display = "none";
    const iframe = document.getElementById("output-iframe");
    const iframeDocument = iframe.contentDocument || iframe.contentWindow.document;
    iframeDocument.open();
    iframeDocument.write(htmlContent + cssContent + jsContent);
    iframeDocument.close();
    iframe.style.display = "block";
});