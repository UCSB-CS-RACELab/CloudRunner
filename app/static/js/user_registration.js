$('#submit-btn').on('click', function(e) {
  /**
   * Need to check for presence of name, email, password, password_conf.
   * Need to check that the password and password confirmation matches.
   * TODO: SSL or encrypt password before sending to server
  **/
  var formInputs = [$('#name'), $('#email'), $('#password'), $('#password_conf')];
  var invalid = false;
  for (var i = 0; i < 4; i++)
  {
    var formInput = formInputs[i];
    if (formInput.val() == '')
    {
      // All inputs are required
      invalid = true;
      // Use bootstraps form control states, which need to be placed on outer div
      var enclosingDiv = formInput.closest('div.form-group');
      // Only need to add this stuff if its not already there
      if (!enclosingDiv.hasClass('has-error'))
      {
        var errorMessageHTML = '<span class="glyphicon glyphicon-remove form-control-feedback"></span>'
        errorMessageHTML += '\n<span class="help-inline text-danger">This field is required.</span>';
        enclosingDiv.addClass('has-error').addClass('has-feedback');
        formInput.after(errorMessageHTML);
      }
    }
    else
    {
      // Need to make sure we remove any errors that we might have placed on it
      var enclosingDiv = formInput.closest('div.form-group');
      if (enclosingDiv.hasClass('has-error'))
      {
        enclosingDiv.removeClass('has-error').removeClass('has-feedback');
        // Here we use the fact that the span.help-inline and span.glyphicon elements
        // will be placed as the next siblings in the DOM
        formInput.next().remove();
        formInput.next().remove();
      }
    }
  }
  if (invalid) {
    // Dont send the POST
    e.preventDefault();
    return;
  }
  // Now we know all the inputs are filled in with at least one character
  var password = formInputs[2];
  var passwordConfirmation = formInputs[3];
  if (password.val() == passwordConfirmation.val()) {
    console.log('Password match!')
  } else {
    // Password mismatch, need to re-enter
    e.preventDefault();
    // Use bootstraps form control states, which need to be placed on outer div
    var errorMessageHTML = '<span class="glyphicon glyphicon-remove form-control-feedback"></span>'
    errorMessageHTML += '\n<span class="help-inline text-danger">Password and password confirmation do not match.</span>';
    password.closest('div.form-group').addClass('has-error').addClass('has-feedback');
    passwordConfirmation.closest('div.form-group').addClass('has-error').addClass('has-feedback');
    password.after(errorMessageHTML);
    passwordConfirmation.after(errorMessageHTML);
  }
});