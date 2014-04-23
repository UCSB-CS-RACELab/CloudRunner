$('#optional-collapse-link').on('click', function(e) {
  var isCollapsed = !$('#optional-collapse-content').hasClass('in');
  if (isCollapsed) {
    $('#optional-collapse-link span').removeClass("glyphicon-collapse-down").addClass("glyphicon-collapse-up");
  } else {
    $('#optional-collapse-link span').removeClass("glyphicon-collapse-up").addClass("glyphicon-collapse-down");
  }
});

function removeMessageAndIcon(input) {
  var enclosingDiv = input.closest('.form-group');
  if (enclosingDiv.hasClass('has-success')) {
    enclosingDiv.removeClass('has-success');
    input.next().remove();
    input.next().remove();
  } else if (enclosingDiv.hasClass('has-error')) {
    enclosingDiv.removeClass('has-error');
    input.next().remove();
    input.next().remove();
  }
}

function addMessageAndIcon(input, success) {
  var enclosingDiv = input.closest('.form-group');
  if (success) {
    var successMessageAndIcon = '<span class="text-success">Upload successful!</span>';
    successMessageAndIcon += '\n<span class="glyphicon glyphicon-ok form-control-feedback"></span>';
    enclosingDiv.addClass('has-success');
    input.after(successMessageAndIcon);
  } else {
    var errorMessageAndIcon = '<span class="text-success">Upload failed!</span>';
    errorMessageAndIcon += '\n<span class="glyphicon glyphicon-remove form-control-feedback"></span>';
    enclosingDiv.addClass('has-error');
    input.after(errorMessageAndIcon);
  }
}

function handleFileSelect(evt) {
  // Called whenever a new file is selected in any of the file inputs
  var originalInput = $(evt.target);
  removeMessageAndIcon(originalInput);
  
  // Check for the various File API support.
  if (!(window.File && window.FileReader && window.FileList && window.Blob)) {
    addMessageAndIcon(originalInput, false);
    alert('The File APIs are not fully supported in this browser and you will not be able to upload files to the server. Please use a different browser.');
    return;
  }
  
  var reader = new FileReader();
  var fileParamName = evt.target.name.split('-')[0];
  
  reader.onerror = function(e) {
    addMessageAndIcon(originalInput, false);
  };
  
  // reader.onprogress = function(e) {
  //   
  // };
  
  // reader.onabort = function(e) {
  //   alert('File read cancelled');
  // };
  
  // reader.onloadstart = function(e) {
  //   document.getElementById('progress_bar').className = 'loading';
  // };
  
  reader.onload = function(e) {
    // Need to make sure we only upload the contents of one file for this parameter...
    var currentFileContentInput = $('input[name='+fileParamName+']');
    if (currentFileContentInput.length > 0) {
      currentFileContentInput.remove();
    }
    var text = reader.result;
    var fileContentInput = $("<input>").attr("type", "hidden").attr("name", fileParamName).val(text);
    $('#job-params-form').append(fileContentInput);
    addMessageAndIcon(originalInput, true);
  }

  // Read in the image file as a binary string.
  reader.readAsText(evt.target.files[0]);
}

$('input[type=file]').on('change', handleFileSelect);
