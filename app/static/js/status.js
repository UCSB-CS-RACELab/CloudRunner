function setDeleteSuccess() {
  // Clear out error messages just in case
  $("#delete-error-infra").text("");
  $("#delete-error-job").text("");
  // Set the success message
  var successMessage = "All selected jobs were successfully deleted.";
  $("#delete-success").text(successMessage);
}

$('.delete-btn').on('click', function(e) {
  e.preventDefault();
  var button = $(this);
  // Button states are part of Bootstrap
  button.button('loading');
  var jobsToDelete = [];
  var checkboxes = document.getElementsByName('select_job');
  for (var i = 0; i < checkboxes.length; i++)
  {
    if (checkboxes[i].checked) {
      jobsToDelete.push(checkboxes[i].value);
    }
  }
  var ajaxData = {
    action: "delete",
    jobs: jobsToDelete
  }
  $.ajax({
    type: "POST",
    url: "/status",
    data: JSON.stringify(ajaxData),
    success: function(data) {
      if (data.success) {
        setDeleteSuccess();
      } else {
        $("#delete-success").text("");
        if (data.infra_error_msg) {
          $("#delete-error-infra").text(data.infra_error_msg);
        }
        if (data.job_error_msg) {
          $("#delete-error-job").text(data.job_error_msg);
        }
      }
      setTimeout(function() {
        button.button('reset');
        window.location.reload();
      }, 2000);
    },
    error: function(data) {
      alert("An unexpected error occurred while processing your request.");
      button.button('reset');
    }
  });
});