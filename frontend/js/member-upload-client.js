(function () {
  "use strict";

  async function startRemoteProjectReview(options) {
    var api = window.DevBareunAPI;
    if (!api || !api.createProject || !api.createUploadUrl || !api.uploadToSignedUrl || !api.startAnalysis) {
      throw new Error("Workspace API client is not ready.");
    }
    var formData = options.formData;
    var files = options.files || [];
    var projectName = options.projectName;
    var analysisType = options.analysisType;
    var setFileState = options.setFileState || function () {};
    var setStatus = options.setStatus || function () {};

    setStatus("Creating protected project workspace...");
    var created = await api.createProject({
      project_name: projectName,
      location: formData.get("location") || "",
      client: formData.get("client") || "",
      project_status: "draft",
      analysis_type: analysisType,
      currency: "AZN"
    });
    var remoteProject = (created && created.project) || created || {};
    var projectId = remoteProject.project_id || remoteProject.id;
    if (!projectId) {
      throw new Error("Project id was not returned by backend.");
    }

    for (var i = 0; i < files.length; i += 1) {
      setFileState(i, "Preparing", 10);
      var upload = await api.createUploadUrl(projectId, files[i]);
      setFileState(i, "Uploading", 35);
      await api.uploadToSignedUrl(Object.assign({ project_id: projectId }, upload), files[i], function (percent) {
        setFileState(i, "Uploading", percent);
      });
      setFileState(i, "Uploaded", 100);
    }

    setStatus("Starting project analysis...");
    var job = await api.startAnalysis(projectId, { analysis_type: analysisType });
    return { projectId: String(projectId), job: job || {} };
  }

  window.DevBareunWorkspaceUpload = {
    startRemoteProjectReview: startRemoteProjectReview
  };
})();
