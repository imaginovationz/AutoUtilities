import React, { useState, useRef } from "react";
import axios from "axios";

const API_BASE = "http://localhost:5000";

export default function PSUpdater() {
  const [psFile, setPsFile] = useState(null);
  const [psDocId, setPsDocId] = useState("");
  const [oldMockFile, setOldMockFile] = useState(null);
  const [oldMockDocId, setOldMockDocId] = useState("");
  const [newMockFile, setNewMockFile] = useState(null);
  const [newMockDocId, setNewMockDocId] = useState("");
  const [status, setStatus] = useState("");
  const [statusLog, setStatusLog] = useState([]);
  const [updatedFilename, setUpdatedFilename] = useState("");
  const [progress, setProgress] = useState(0);
  const [progressStatus, setProgressStatus] = useState("");
  const [currentJobId, setCurrentJobId] = useState("");
  const pollIntervalRef = useRef(null);

  const logStatus = (updates) => {
    if (!updates) return;
    setStatusLog(updates);
    setStatus(updates[updates.length - 1] || "");
  };

  // [1] Upload Old PS
  const uploadPS = async () => {
    if (!psFile) return alert("Select Old PS (docx)");
    const form = new FormData();
    form.append("file", psFile);
    setStatus("Uploading Old PS...");
    setStatusLog(["Uploading Old PS..."]);
    try {
      const res = await axios.post(`${API_BASE}/upload_ps`, form, { headers: { "Content-Type": "multipart/form-data" }});
      setPsDocId(res.data.doc_id);
      logStatus(res.data.status_updates);
    } catch (err) {
      console.error(err);
      setStatus("Error uploading Old PS: " + (err.response?.data?.error || err.message));
      setStatusLog([status]);
    }
  };

  // [1a] Upload Old Mockup
  const uploadOldMock = async () => {
    if (!oldMockFile) return alert("Select Old Mockup (docx)");
    const form = new FormData();
    form.append("file", oldMockFile);
    setStatus("Uploading Old Mockup...");
    setStatusLog(["Uploading Old Mockup..."]);
    try {
      const res = await axios.post(`${API_BASE}/upload_old_mock`, form, { headers: { "Content-Type": "multipart/form-data" }});
      setOldMockDocId(res.data.doc_id);
      logStatus(res.data.status_updates);
    } catch (err) {
      console.error(err);
      setStatus("Error uploading Old Mockup: " + (err.response?.data?.error || err.message));
      setStatusLog([status]);
    }
  };

  // [2] Upload New Mockup
  const uploadNewMock = async () => {
    if (!newMockFile) return alert("Select New Mockup (docx)");
    const form = new FormData();
    form.append("file", newMockFile);
    setStatus("Uploading New Mockup...");
    setStatusLog(["Uploading New Mockup..."]);
    try {
      const res = await axios.post(`${API_BASE}/upload_new_mock`, form, { headers: { "Content-Type": "multipart/form-data" }});
      setNewMockDocId(res.data.doc_id);
      logStatus(res.data.status_updates);
    } catch (err) {
      console.error(err);
      setStatus("Error uploading New Mockup: " + (err.response?.data?.error || err.message));
      setStatusLog([status]);
    }
  };

  // Progress polling
  const pollProgress = (jobId) => {
    if (!jobId) return;
    axios.get(`${API_BASE}/progress/${jobId}`)
      .then(res => {
        const { progress, status } = res.data;
        setProgress(progress || 0);
        setProgressStatus(status || "");
        if (progress < 100) {
          pollIntervalRef.current = setTimeout(() => pollProgress(jobId), 1000);
        } else {
          clearTimeout(pollIntervalRef.current);
        }
      })
      .catch(err => {
        setProgress(0);
        setProgressStatus("Error fetching progress.");
        clearTimeout(pollIntervalRef.current);
      });
  };

  // [3][4] Generate New PS
  const generateNewPS = async () => {
    if (!psDocId || !oldMockDocId || !newMockDocId)
      return alert("Upload Old PS, Old Mockup, and New Mockup first.");
    setStatus("Generating New PS document (this may take a while)...");
    setStatusLog(["Generating New PS document (this may take a while)..."]);
    setProgress(0);
    setProgressStatus("Starting...");
    setUpdatedFilename("");
    try {
      const res = await axios.post(`${API_BASE}/generate_new_ps`, {
        ps_doc_id: psDocId,
        old_mock_id: oldMockDocId,
        new_mock_id: newMockDocId
      });
      setUpdatedFilename(res.data.updated_file);
      logStatus(res.data.status_updates);
      const jobId = res.data.job_id;
      setCurrentJobId(jobId);
      pollProgress(jobId);
    } catch (err) {
      console.error(err);
      setStatus("Error generating New PS: " + (err.response?.data?.error || err.message));
      setStatusLog([status]);
      setProgress(0);
      setProgressStatus("Error generating New PS.");
    }
  };

  const downloadUpdated = () => {
    if (!updatedFilename) return alert("No updated file");
    window.open(`${API_BASE}/download/${encodeURIComponent(updatedFilename)}`, "_blank");
  };

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
    };
  }, []);

  return (
    <div style={{ maxWidth: 800 }}>
      <section style={{ marginBottom: 16 }}>
        <h3>Step 1 — Upload Old PS (Original requirement document)</h3>
        <input type="file" accept=".docx" onChange={e => setPsFile(e.target.files[0])} />
        <button onClick={uploadPS} style={{ marginLeft: 8 }}>Upload Old PS</button>
      </section>
      <section style={{ marginBottom: 16 }}>
        <h3>Step 2 — Upload Old Mockup document</h3>
        <input type="file" accept=".docx" onChange={e => setOldMockFile(e.target.files[0])} />
        <button onClick={uploadOldMock} style={{ marginLeft: 8 }}>Upload Old Mockup</button>
      </section>
      <section style={{ marginBottom: 16 }}>
        <h3>Step 3 — Upload New Mockup document</h3>
        <input type="file" accept=".docx" onChange={e => setNewMockFile(e.target.files[0])} />
        <button onClick={uploadNewMock} style={{ marginLeft: 8 }}>Upload New Mockup</button>
      </section>
      <section style={{ marginBottom: 16 }}>
        <h3>Step 4 — Generate New PS</h3>
        <button onClick={generateNewPS}>Generate New PS document</button>
      </section>
      <section style={{ marginBottom: 16 }}>
        <h3>Step 5 — Download</h3>
        <button onClick={downloadUpdated} disabled={!updatedFilename}>Download New PS</button>
      </section>
	  
	  {/* Progress Bar */}
	          
	  		
	  		<div style={{ marginTop: 16 }}>
	  		  <strong>Progress:</strong>
	  		  <div style={{
	  		    width: "100%",
	  		    background: "#ccc",
	  		    height: 30,
	  		    borderRadius: 5,
	  		    marginTop: 6,
	  		    boxShadow: "inset 0 1px 3px #aaa"
	  		  }}>
	  		    <div
	  		      style={{
	  		        width: `${progress}%`,
	  		        background: progress < 100 ? "#2196f3" : "#388e3c", // blue while processing, dark green when done
	  		        height: "100%",
	  		        color: "#fff",
	  		        textAlign: "center",
	  		        borderRadius: 5,
	  		        transition: "width 0.5s",
	  		        fontWeight: "bold",
	  		        display: "flex",
	  		        alignItems: "center",
	  		        justifyContent: "center",
	  		        fontSize: 16,
	  		        boxShadow: progress > 0 ? "0 0 6px #2196f3" : "none"
	  		      }}
	  		    >
	                {progressStatus} {progress}%
	              </div>
	  			
	  			
	  			
	            </div>
	          </div>
			  
      <div style={{ marginTop: 20 }}>
        <strong>Status:</strong> <span>{status}</span>
        
		
		<div style={{ marginTop: 10 }}>
          <strong>Status Log:</strong>
          <ul>
            {statusLog.map((msg, idx) => (
              <li key={idx}>{msg}</li>
            ))}
          </ul>
        </div>
		
		
        
		
		
      </div>
    </div>
  );
}