# Solution Implementation

* [Overview](#overview)
* [Setting Layer](#setting-layer)
* [Setting Lambda](#setting-lambda)
* [Test](#test)
* [Adding An Event Trigger On The S3 Bucket](#adding-an-event-trigger-on-the-s3-bucket)
* [Testing And Monitoring](#testing-and-monitoring)

<br><br>

# Overview
This Implemntation is explain [the video on the url](https://drive.google.com/file/d/1-lXPw-NdqrX-zOhNRG_CDK3qIM1akb69/view), describe the lambda function how to setting the services and how to allow accesses between services

<br><br>

# Setting Layer
We can download the required version of the Pillow library within a Docker container and then deploy it directly to a Lambda layer.

We can also use this method as alternative
1. Open the AWS CloudShell.
2. Upgrade Python to version 3.12:
```sh
sudo dnf install -y python3.12 python3.12-pip zip
```

3. Install the `Pillow` library inside the pillow-layer/python folder:
```sh
pip3.12 install Pillow --target ~/pillow-layer/python
```

4. Upload the `watermark image` into the pillow-layer/resources folder:
```sh
cp watermark.png ~/pillow-layer/resources/
```
```txt
pillow-layer/
|---python/
    |------Pillow files here
|---resources/
    |------watermark.png
```

5. Create a `zip file` so the folder can be installed as an AWS Lambda layer:
```sh
cd ~/pillow-layer
zip -r pillow_layer_watermarck.zip .
```

6. Publish the layer so it can be used by Lambda functions
```sh
aws lambda publish-layer-version \
  --layer-name PillowWaterLayer \
  --description "Pillow with watermark for Python 3.12" \
  --zip-file fileb://pillow_layer_watermarck.zip \
  --compatible-runtimes python3.12
```

<br><br>

# Setting Lambda
1. First, create a Lambda function using the Python runtime version 3.12.
2. Configure the function timeout to 20 seconds, since some images may take longer to process and save.
3. Configure access so the Lambda function can read from the source (uploaded) bucket and write the modified copy to the destination bucket. Add an inline policy to grant this access. [You can check policy here](./S3AccessPolicy.json)
4. Add the previously created layer to allow the Python code to use Pillow for image processing and watermarking.
5. Finally, deploy the [Python code](./Lambda-Function.py). Lambda provides integrated VS Code support to simplify code deployment.

<br><br>

# Test
1. Upload an image to the upload bucket.
2. In the Lambda console, navigate to the Test tab.
3. Specify the test event. In our case, it should simulate an `S3 Put` action.
4. Add the test JSON file `TestLambda.json` and update it with the uploaded image name and source bucket so the Python code `can access the image`.
5. We check if the function is work correctly (It returns short access link of the modify image)

<br><br>

# Adding An Event Trigger On The S3 Bucket
1. Navigate to the Properties tab of the upload bucket.
2. Go to Event notifications.
3. Add a new event notification and select the Lambda function you created as the trigger (Ensures that whenever a new image is uploaded, the Lambda function is automatically invoked to create the modified copy).

<br><br>

# Testing and Monitoring
1. Upload an image to the upload bucket
3. Check the destination bucket to verify that the modified copy has been created.
2. Track and monitor the Lambda execution using Amazon CloudWatch Logs. (This helps confirm that the function is running as expected and allows you to debug any errors)