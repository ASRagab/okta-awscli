""" Wrapper script for awscli which handles Okta auth """
#pylint: disable=C0325
from subprocess import call
import logging
from oktaawscli.okta_auth import OktaAuth
from oktaawscli.aws_auth import AwsAuth
import click

def get_credentials(aws_auth, okta_profile, profile, verbose, logger):
    """ Gets credentials from Okta """
    okta = OktaAuth(okta_profile, verbose, logger)
    app_name, assertion, selected_role = okta.get_assertion()
    app_name = app_name.replace(" ", "")
    if selected_role:
        role = selected_role
    else:
        role = aws_auth.choose_aws_role(assertion)
    principal_arn, role_arn = role

    token = aws_auth.get_sts_token(role_arn, principal_arn, assertion)
    access_key_id = token['AccessKeyId']
    secret_access_key = token['SecretAccessKey']
    session_token = token['SessionToken']
    if not profile:
        console_output(access_key_id, secret_access_key, session_token, verbose)
        exit(0)
    else:
        aws_auth.write_sts_token(profile, access_key_id, secret_access_key, session_token)

def console_output(access_key_id, secret_access_key, session_token, verbose):
    """ Outputs STS credentials to console """
    if verbose:
        print("Use these to set your environment variables:")
    print("export AWS_ACCESS_KEY_ID=%s" % access_key_id)
    print("export AWS_SECRET_ACCESS_KEY=%s" % secret_access_key)
    print("export AWS_SESSION_TOKEN=%s" % session_token)

#pylint: disable=R0913
@click.command()
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode')
@click.option('-d', '--debug', is_flag=True, help='Enables debug mode')
@click.option('-f', '--force', is_flag=True, help='Forces new STS credentials. \
Skips STS credentials validation.')
@click.option('--okta-profile', help="Name of the profile to use in .okta-aws. \
If none is provided, then the default profile will be used.")
@click.option('--profile', help="Name of the profile to store temporary \
credentials in ~/.aws/credentials. If profile doesn't exist, it will be created. If omitted, credentials \
will output to console.")
@click.argument('awscli_args', nargs=-1, type=click.UNPROCESSED)
def main(okta_profile, profile, verbose, debug, force, awscli_args):
    """ Authenticate to awscli using Okta """
    ## Set up logging
    logger = logging.getLogger('okta-awscli')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARN)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if verbose:
        handler.setLevel(logging.INFO)
    if debug:
        handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    if not okta_profile:
        okta_profile = "default"
    aws_auth = AwsAuth(profile, verbose, logger)
    if not aws_auth.check_sts_token(profile) or force:
        if force and profile:
            logger.info("Force option selected, getting new credentials anyway.")
        elif force:
            logger.info("Force option selected, but no profile provided. Option has no effect.")
        get_credentials(aws_auth, okta_profile, profile, verbose, logger)

    if awscli_args:
        cmdline = ['aws', '--profile', profile] + list(awscli_args)
        logger.info('Invoking: %s' % ' '.join(cmdline))
        call(cmdline)

if __name__ == "__main__":
    #pylint: disable=E1120
    main()
    #pylint: enable=E1120
