def handle_generate_file(request):
    from turingarena_cloud.s3_files import generate_cloud_files
    from turingarena_cloud.dynamodb_files import mark_file_generated

    url = generate_cloud_files(request.working_directory)
    mark_file_generated(request.file_id, url)
